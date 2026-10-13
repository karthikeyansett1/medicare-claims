"""Run fixture builds in an isolated output tree; canonical evidence is read-only.

The source checkout's .env is never copied. Database settings must be explicit in
fixture mode, and fixture database names must end in _ci to protect local data.
"""
import csv
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import yaml

from ingest.download import ROOT, read_manifest, save_manifest, sha256

EXCLUDED = {'.git', '.env', '.venv', '.python', '.pytest_cache', '__pycache__', '.runtime', 'target', 'logs', 'dbt_packages'}


def output_directory(root, requested):
    target = Path(requested).resolve()
    root = Path(root).resolve()
    if target == root or target in root.parents or (root in target.parents and '.runtime' not in target.relative_to(root).parts):
        raise ValueError('OUTPUT_ROOT must be external or under .runtime; never overwrite source artifacts')
    if target.exists() and any(target.iterdir()):
        raise ValueError('OUTPUT_ROOT must be empty; choose a fresh run directory')
    return target


def prepare(root, destination, fixtures):
    destination = output_directory(root, destination)
    def ignore(directory, names):
        omitted = {n for n in names if n in EXCLUDED or n.startswith('.env')}
        if Path(directory) == root/'data':
            omitted |= {'raw', 'extracted'}
        if any((Path(directory)/n).is_symlink() for n in set(names)-omitted):
            raise ValueError('Runtime source must not contain symlinks')
        return omitted
    shutil.copytree(root, destination, ignore=ignore, dirs_exist_ok=True)
    info = json.loads((fixtures/'fixture.json').read_text())
    shutil.copytree(fixtures, destination/'data/fixtures', dirs_exist_ok=True)
    expected = {v['filename'].replace('.zip','.csv') for v in yaml.safe_load((root/'ingest/urls.yaml').read_text())['samples'][1].values()}
    if set(info['files']) != expected or info['sample'] != 1 or len(set(info['member_ids'])) != 1000:
        raise ValueError('Fixture must contain exactly eight Sample 1 files and 1000 distinct members')
    members = set(info['member_ids'])
    anchors = json.loads((fixtures/'anchors.json').read_text())
    anchor_ids = set(anchors['member_ids'])
    if info['member_count'] != 1000 or info['seed'] != 15 or info['anchored_members'] != len(anchor_ids) or not anchor_ids <= members:
        raise ValueError('Fixture selection metadata does not match anchored cohort')
    baseline = json.loads((root/'docs/data_profile.json').read_text())
    schemas = {item['file']: item['columns'] for item in baseline['files'].values()}
    observed = set()
    manifests = read_manifest(destination/'data/manifest.csv')
    for name, record in info['files'].items():
        if Path(name).name != name or not name.endswith('.csv'):
            raise ValueError('Unsafe fixture filename')
        archive = fixtures/(name+'.gz')
        if sha256(archive) != record['compressed_sha256']:
            raise ValueError('Fixture archive hash mismatch')
        output = destination/'data/extracted/sample_1'/name
        output.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(archive,'rb') as source, output.open('wb') as target:
            shutil.copyfileobj(source,target)
        if sha256(output) != record['sha256']:
            raise ValueError('Fixture content hash mismatch')
        with output.open(newline='') as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            if reader.fieldnames != schemas[name] or len(reader.fieldnames) != len(set(reader.fieldnames)) or any(None in row or row['DESYNPUF_ID'] not in members for row in rows):
                raise ValueError('Invalid fixture schema or cohort')
            if len(rows) != record['rows']:
                raise ValueError('Fixture row count mismatch')
            observed.update(row['DESYNPUF_ID'] for row in rows)
        relative = output.relative_to(destination).as_posix()
        original = manifests[relative]
        manifests[relative] = dict(original, sha256=record['sha256'], size_bytes=output.stat().st_size,
                                   source_url='fixture:seed-15', resolved_url='fixture:seed-15')
    if observed != members:
        raise ValueError('Fixture member population mismatch')
    (destination/'.fixture-runtime').write_text('isolated fixture runtime\n')
    save_manifest(destination/'data/manifest.csv', manifests)
    return destination


def guard():
    required = ['PG_HOST','PG_PORT','PG_USER','PG_PASSWORD','PG_DB','ASSISTANT_PG_PASSWORD']
    if any(not os.getenv(k) for k in required) or not os.environ['PG_DB'].endswith('_ci'):
        raise ValueError('Fixture builds require explicit PG settings and a database name ending _ci')


def main():
    guard()
    fixtures = Path(os.getenv('DATA_DIR', str(ROOT/'data/fixtures'))).resolve()
    destination = prepare(ROOT, os.getenv('OUTPUT_ROOT', str(ROOT/'.runtime/ci')), fixtures)
    env = dict(os.environ, DATA_DIR='data/extracted', MEDICARE_SAMPLES='1',
               FIXTURE_MANIFEST=str(destination/'data/fixtures/fixture.json'), RUN_DB_TESTS='1')
    # Use the caller's pinned environment, while importing only copied runtime code.
    env.pop('PYTHONPATH', None)
    env.pop('MAKEFLAGS', None)
    env.pop('MAKEOVERRIDES', None)
    env.pop('MFLAGS', None)
    command = ['make', '_fixture-pipeline', 'PYTHON='+sys.executable, 'MEDICARE_SAMPLES=1']
    print(f'Fixture runtime and all generated evidence: {destination}', flush=True)
    raise SystemExit(subprocess.run(command, cwd=destination, env=env).returncode)


if __name__ == '__main__':
    if '--guard' in sys.argv:
        guard()
        if not (ROOT/'.fixture-runtime').is_file():
            raise ValueError('Internal fixture pipeline requires isolated runtime')
        from ingest.db import get_conn
        with get_conn() as conn:
            others = conn.execute("select datname from pg_database where not datistemplate and datname not in ('postgres',current_database())").fetchall()
            objects = conn.execute("select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname not in ('pg_catalog','information_schema') and n.nspname not like 'pg_toast%' limit 1").fetchall()
            role = conn.execute("select 1 from pg_roles where rolname='assistant_ro'").fetchall()
            if others or objects or role:
                raise ValueError('Fixture CI requires an empty dedicated PostgreSQL cluster; other databases, objects or assistant role found')
    else:
        main()
