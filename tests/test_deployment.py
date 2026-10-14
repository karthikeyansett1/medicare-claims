"""Deployment boundary tests: no credentials, member IDs or callable AI in public bundle."""
import json
from pathlib import Path
from deployment.build_static import build
from deployment.build_docker import build as build_docker
from dashboard.data import FORBIDDEN

def test_static_bundle_privacy_and_scope(tmp_path):
    build(tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == {'README.md','index.html','app.js','style.css','data.json','measure_definitions.md'}
    data=json.loads((tmp_path/'data.json').read_text())
    assert data['manifest']['samples']==[1,2]
    assert len(data['providers'])==872
    for key in ('providers','overview','conditions','comparison','pairs','coverage'):
        for row in data[key]: assert not FORBIDDEN.intersection(row)
    assert len(data['demo']['examples'])==4
    for example in data['demo']['examples']:
        assert example['rows']
        for row in example['rows']: assert not FORBIDDEN.intersection(row)
    js=(tmp_path/'app.js').read_text()
    assert "fetch('data.json')" in js
    assert 'postgres://' not in js and 'postgresql://' not in js

def test_docker_bundle_is_demo_only(tmp_path):
    build_docker(tmp_path)
    assert not (tmp_path/'assistant/sql_agent.py').exists()
    assert not (tmp_path/'.env').exists()
    assert 'ENABLE_LIVE_ASSISTANT=false' in (tmp_path/'Dockerfile').read_text()
    assert (tmp_path/'assistant/demo.py').exists()

def test_demo_ui_never_imports_agent():
    source=(Path(__file__).resolve().parents[1]/'assistant/demo.py').read_text()
    assert 'sql_agent' not in source
    assert 'psycopg' not in source


def test_static_builder_refuses_unexpected_existing_files(tmp_path):
    import pytest
    (tmp_path/'.env').write_text('private sentinel')
    with pytest.raises(ValueError, match='allowlist'):
        build(tmp_path)
    assert not (tmp_path/'data.json').exists()
