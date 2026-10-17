"""Fixture identity, provenance and isolation are contracts, not full-data golds."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import pytest
from ingest.download import ROOT
from ingest.make_fixture import select_members
from ingest.runtime import output_directory


def test_selection_stable_unique_and_anchored():
    people = [f'{i:016X}' for i in range(1500)]
    chosen = select_members(people, people[:40])
    assert chosen == select_members(reversed(people), people[:40])
    assert len(chosen) == 1000 and set(people[:40]) <= chosen
    with pytest.raises(ValueError):
        select_members(people, ['missing'])


def test_committed_fixture_identity_and_hashes():
    directory = ROOT/'data/fixtures'
    info = json.loads((directory/'fixture.json').read_text())
    members = set(info['member_ids'])
    assert len(members) == info['member_count'] == 1000
    assert len(info['files']) == 8
    assert sum(p.stat().st_size for p in directory.iterdir()) < 10_000_000
    observed = set()
    for name, record in info['files'].items():
        archive = directory/(name+'.gz')
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == record['compressed_sha256']
        content = gzip.decompress(archive.read_bytes())
        assert hashlib.sha256(content).hexdigest() == record['sha256']
        rows = list(csv.DictReader(content.decode().splitlines()))
        assert len(rows) == record['rows']
        assert all(r['DESYNPUF_ID'] in members for r in rows)
        observed.update(r['DESYNPUF_ID'] for r in rows)
        assert len(rows[0]) == len(set(rows[0]))
    assert observed == members


def test_runtime_cannot_overwrite_sources(tmp_path):
    root = tmp_path/'source'
    root.mkdir()
    for target in (root, tmp_path, root/'docs', root/'data'):
        with pytest.raises(ValueError):
            output_directory(root, target)
    assert output_directory(root, root/'.runtime/new') == root/'.runtime/new'
    full = tmp_path/'run'; full.mkdir(); (full/'evidence').write_text('preserve')
    with pytest.raises(ValueError):
        output_directory(root, full)


def test_prepare_preserves_source_and_separates_fixture_baseline(tmp_path):
    from ingest.runtime import prepare
    protected = [ROOT/'data/manifest.csv', ROOT/'docs/data_profile.json', ROOT/'analysis/risk_model_diagnostics.json', ROOT/'dashboard/data/manifest.json']
    before = [p.read_bytes() for p in protected]
    output = prepare(ROOT, tmp_path/'runtime', ROOT/'data/fixtures')
    assert not (output/'.env').exists()
    assert (output/'.fixture-runtime').exists()
    assert [p.read_bytes() for p in protected] == before
    assert (output/'data/manifest.csv').read_bytes() != before[0] or (ROOT/'.fixture-runtime').exists()
    info = json.loads((output/'data/fixtures/fixture.json').read_text())
    for name, record in info['files'].items():
        assert hashlib.sha256((output/'data/extracted/sample_1'/name).read_bytes()).hexdigest() == record['sha256']
