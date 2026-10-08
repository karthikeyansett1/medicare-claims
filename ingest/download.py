"""Acquire public source files with auditable hashes and strict sample validation.

Run from any directory: python -m ingest.download [--verify-only].
No remote writes or Git operations occur. Failed files leave no final download.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import unquote, urlparse
import zipfile

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm
import yaml

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['path', 'kind', 'sample_id', 'file_type', 'size_bytes', 'sha256',
          'downloaded_at_utc', 'source_url', 'resolved_url', 'parent_archive']


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def check_sample(name, expected):
    """Exact token matching: sample_1 must never accept sample_10 or sample_20."""
    token = re.search(r'_sample_(\d+)(?:[ab])?(?=\.|$)', name, re.I)
    if not token or int(token.group(1)) != expected:
        raise ValueError(f'Wrong sample: expected {expected}, got {name}')


def validate_name(name):
    if not name or Path(name).name != name or '\\' in name or name in ('.', '..'):
        raise ValueError(f'Unsafe filename: {name}')


def artifacts(config, sample):
    for file_type, spec in config['samples'][sample].items():
        yield dict(spec, sample_id=sample, file_type=file_type, kind='zip')
    for file_type, spec in config['references'].items():
        yield dict(spec, sample_id='', file_type=file_type)


def read_manifest(path):
    if not path.exists():
        return {}
    with path.open(newline='') as stream:
        return {row['path']: row for row in csv.DictReader(stream)}


def save_manifest(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.csv.part')
    with temporary.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows[key] for key in sorted(rows))
    temporary.replace(path)


def verify_record(path, record):
    if not path.is_file() or path.stat().st_size != int(record['size_bytes']):
        raise ValueError(f'Missing file or size mismatch: {path.name}')
    if sha256(path) != record['sha256']:
        raise ValueError(f'SHA-256 mismatch: {path.name}; remove the corrupt file and rerun download')


def archive_members(path, spec):
    """Inspect all members before writing any of them; extraction verifies CRCs."""
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if not members:
            raise ValueError('Empty archive')
        names = set()
        for member in members:
            validate_name(member.filename)
            if member.is_dir() or member.filename.lower() in names:
                raise ValueError('Unexpected directory or duplicate ZIP member')
            names.add(member.filename.lower())
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('ZIP symlinks are not allowed')
            if member.file_size > 15 * 1024**3:
                raise ValueError('ZIP member exceeds 15 GiB limit')
            if spec['sample_id']:
                check_sample(member.filename, spec['sample_id'])
                if member.filename.lower() != spec['filename'][:-4].lower() + '.csv':
                    raise ValueError(f'Unexpected CSV for this archive: {member.filename}')
        if spec['sample_id'] and len(members) != 1:
            raise ValueError('Expected exactly one claims CSV per archive')
        return members


def fetch(session, spec, root, rows, verify_only=False):
    name = spec['filename']
    validate_name(name)
    if spec['sample_id']:
        check_sample(name, spec['sample_id'])
        check_sample(unquote(urlparse(spec['url']).path).split('/')[-1], spec['sample_id'])
    folder = 'data/raw' if spec['kind'] == 'zip' else 'data/reference/documentation'
    path = root / folder / name
    key = path.relative_to(root).as_posix()
    previous = rows.get(key)
    if previous and path.exists():
        if previous['source_url'] != spec['url']:
            raise ValueError(f'Source URL changed for {name}; review provenance before replacing it')
        verify_record(path, previous)
        print(f'VERIFIED cached {name}', flush=True)
        return path, previous
    if verify_only:
        raise ValueError(f'No verified local download: {name}')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.part')
    try:
        with session.get(spec['url'], stream=True, timeout=(15, 90)) as response:
            response.raise_for_status()
            if spec['sample_id']:
                check_sample(unquote(urlparse(response.url).path).split('/')[-1], spec['sample_id'])
            expected_size = int(response.headers.get('Content-Length', 0))
            with temporary.open('wb') as stream, tqdm(
                total=expected_size or None, unit='B', unit_scale=True,
                desc=name, disable=not sys.stderr.isatty(),
            ) as progress:
                for block in response.iter_content(1024 * 1024):
                    stream.write(block)
                    progress.update(len(block))
            if expected_size and not response.headers.get('Content-Encoding'):
                if temporary.stat().st_size != expected_size:
                    raise ValueError(f'Incomplete response: {name}')
            if spec['kind'] == 'zip':
                archive_members(temporary, spec)
                with zipfile.ZipFile(temporary) as archive:
                    bad = archive.testzip()
                    if bad:
                        raise ValueError(f'CRC failure in {bad}')
            else:
                with temporary.open('rb') as stream:
                    if stream.read(5) != b'%PDF-':
                        raise ValueError(f'Expected PDF, got another format: {name}')
            digest = sha256(temporary)
            if previous and digest != previous['sha256']:
                raise ValueError(f'Source content changed from recorded hash: {name}')
            temporary.replace(path)
            row = dict(path=key, kind=spec['kind'], sample_id=spec['sample_id'],
                       file_type=spec['file_type'], size_bytes=path.stat().st_size,
                       sha256=digest, downloaded_at_utc=datetime.now(timezone.utc).isoformat(),
                       source_url=spec['url'], resolved_url=response.url, parent_archive='')
            # Preserve acquisition date on identical re-downloads.
            return path, previous or row
    finally:
        temporary.unlink(missing_ok=True)


def extract(path, spec, root, rows, parent, verify_only=False):
    folder = (f"data/extracted/sample_{spec['sample_id']}" if spec['sample_id']
              else 'data/reference/ccs_2015')
    members = archive_members(path, spec)
    with zipfile.ZipFile(path) as archive:
        for member in members:
            target = root / folder / member.filename
            key = target.relative_to(root).as_posix()
            previous = rows.get(key)
            if previous and target.exists():
                verify_record(target, previous)
                continue
            if verify_only:
                raise ValueError(f'Missing verified extraction: {key}')
            target.parent.mkdir(parents=True, exist_ok=True)
            if shutil.disk_usage(target.parent).free < member.file_size + 1024**3:
                raise ValueError(f'Insufficient free space to extract {member.filename}')
            temporary = target.with_suffix(target.suffix + '.part')
            try:
                with archive.open(member) as source, temporary.open('wb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                if spec['sample_id']:
                    with temporary.open(newline='', encoding='utf-8-sig') as stream:
                        header = next(csv.reader(stream))
                    if 'DESYNPUF_ID' not in header or len(header) != len(set(header)):
                        raise ValueError(f'Invalid claims CSV header: {member.filename}')
                digest = sha256(temporary)
                if previous and digest != previous['sha256']:
                    raise ValueError(f'Extraction differs from recorded hash: {member.filename}')
                temporary.replace(target)
                rows[key] = previous or dict(parent, path=key, kind='extracted',
                    size_bytes=target.stat().st_size, sha256=digest,
                    parent_archive=parent['path'])
            finally:
                temporary.unlink(missing_ok=True)


def run(config_path, root, sample=1, verify_only=False):
    config = yaml.safe_load(config_path.read_text())
    manifest = root / 'data/manifest.csv'
    rows = read_manifest(manifest)
    errors = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'medicare-claims-educational-project/0.1'})
    session.mount('https://', HTTPAdapter(max_retries=Retry(
        total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))
    try:
        for spec in artifacts(config, sample):
            try:
                path, row = fetch(session, spec, root, rows, verify_only)
                rows[row['path']] = row
                if spec['kind'] == 'zip':
                    extract(path, spec, root, rows, row, verify_only)
                print(f"PASS {spec['file_type']}", flush=True)
            except (requests.RequestException, ValueError, OSError, zipfile.BadZipFile, EOFError) as exc:
                errors.append({'file_type': spec['file_type'], 'error': str(exc)})
                print(f"FAIL {spec['file_type']}: {exc}", flush=True)
            finally:
                if not verify_only:
                    save_manifest(manifest, rows)
    finally:
        session.close()
    report = dict(sample=sample, verified_at_utc=datetime.now(timezone.utc).isoformat(),
                  mode='verify-only' if verify_only else 'download', success=not errors, errors=errors)
    report_path = root / 'docs/download_verification.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample', type=int, default=1)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    return run(ROOT / 'ingest/urls.yaml', ROOT, args.sample, args.verify_only)


if __name__ == '__main__':
    raise SystemExit(main())
