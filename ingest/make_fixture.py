"""Reproduce a 1,000-member stratified Sample 1 fixture without altering sources.

All rows for the selected IDs are retained byte-for-byte; dates and source schemas
are unchanged. Gzip timestamps and filenames are fixed for reproducible archives.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random

from ingest.download import ROOT, sha256, read_manifest, verify_record


def select_members(population, anchors, count=1000, seed=15):
    population, anchors = set(population), set(anchors)
    if not anchors <= population or len(anchors) > count or len(population) < count:
        raise ValueError('Invalid anchor population or fixture size')
    return anchors | set(random.Random(seed).sample(sorted(population - anchors), count - len(anchors)))


def make_fixture(source, destination):
    anchors = json.loads((destination / 'anchors.json').read_text())
    paths = sorted(source.glob('*.csv'))
    if len(paths) != 8:
        raise ValueError('Expected all eight Sample 1 source CSVs')
    manifest = read_manifest(ROOT/'data/manifest.csv')
    for path in paths:
        verify_record(path, manifest['data/extracted/sample_1/'+path.name])
    population = set()
    for path in paths:
        if 'beneficiary' in path.name.lower():
            with path.open(newline='') as stream:
                population.update(row['DESYNPUF_ID'] for row in csv.DictReader(stream))
    members = select_members(population, anchors['member_ids'])
    report = dict(sample=1, member_count=len(members), seed=15, anchored_members=len(anchors['member_ids']),
                  selection='Stratified: fixed provider-panel anchors plus seeded random remaining members',
                  member_ids=sorted(members), files={})
    selected = {m.encode() for m in members}
    for path in paths:
        target = destination / (path.name + '.gz')
        count, digest = 0, hashlib.sha256()
        with path.open('rb') as stream, target.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as out:
            header = stream.readline()
            if header.split(b',',1)[0].strip(b'"') != b'DESYNPUF_ID':
                raise ValueError('Member ID must be first column')
            out.write(header); digest.update(header)
            for line in stream:
                if line.split(b',',1)[0].strip(b'"') in selected:
                    out.write(line); digest.update(line); count += 1
        report['files'][path.name] = dict(rows=count, sha256=digest.hexdigest(), compressed_sha256=sha256(target), source_sha256=sha256(path), compressed_bytes=target.stat().st_size)
        print(path.name, count, flush=True)
    (destination/'fixture.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'data/extracted/sample_1')
    parser.add_argument('--destination', type=Path, default=ROOT/'data/fixtures')
    args = parser.parse_args()
    make_fixture(args.source, args.destination)
