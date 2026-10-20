from pathlib import Path
from types import SimpleNamespace
import pytest
from deployment.live import prepare


def setup(monkeypatch,tmp_path):
    monkeypatch.setattr(prepare,'ROOT',tmp_path)
    monkeypatch.setattr('sys.argv',['prepare','--apply-bootstrap'])
    monkeypatch.setattr(prepare,'dotenv_values',lambda path:{'DEPLOY_DATABASE_URL':'postgresql://admin:secret@host/db',
        'DEPLOY_ASSISTANT_DATABASE_URL':'postgresql://medicare_demo_ro:pw@host/db','LLM_API_KEY':'unit-test-key'})
    monkeypatch.setattr(prepare.os,'environ',{})
    events=[]
    class Conn:
        info=SimpleNamespace(dbname='db')
        def __enter__(self):events.append('begin');return self
        def execute(self,query,*args):
            events.append('sql');return SimpleNamespace(fetchone=lambda:(False,))
        def __exit__(self,kind,*args):events.append('rollback' if kind else 'commit')
    monkeypatch.setattr(prepare.psycopg,'connect',lambda *args,**kwargs:Conn())
    return events


def test_private_file_durable_before_commit(monkeypatch,tmp_path):
    events=setup(monkeypatch,tmp_path)
    fsync=prepare.os.fsync
    def sync(fd):events.append('fsync');return fsync(fd)
    monkeypatch.setattr(prepare.os,'fsync',sync)
    prepare.main()
    target=tmp_path/'.runtime/streamlit-live-secrets.toml'
    assert target.exists() and target.stat().st_mode&0o777==0o600
    assert events.index('fsync')<events.index('commit')
    assert 'sslmode=verify-full' in target.read_text()
    assert 'sslrootcert' not in target.read_text()


def test_file_write_failure_rolls_back_without_reset(monkeypatch,tmp_path):
    events=setup(monkeypatch,tmp_path)
    monkeypatch.setattr(prepare.os,'fsync',lambda fd:(_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError):prepare.main()
    assert 'rollback' in events and 'commit' not in events
    assert not (tmp_path/'.runtime/streamlit-live-secrets.toml').exists()
