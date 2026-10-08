"""Exercise wrong-source, corrupt-download, and safe-rerun failure modes offline."""
import csv
from pathlib import Path
import zipfile

import pytest

from ingest.download import archive_members, check_sample, extract, fetch


def spec():
    return dict(filename='DE1_0_2010_Beneficiary_Summary_File_Sample_1.zip',
                url='https://example.test/DE1_0_2010_Beneficiary_Summary_File_Sample_1.zip',
                sample_id=1, file_type='beneficiary_2010', kind='zip')


@pytest.mark.parametrize('name', ['file_sample_10.zip', 'file_sample_20.zip',
                                    'file_sample_1A_fake.zip', 'file.zip'])
def test_rejects_wrong_sample(name):
    with pytest.raises(ValueError, match='Wrong sample'):
        check_sample(name, 1)


@pytest.mark.parametrize('name', ['file_sample_1.zip', 'file_sample_1A.zip',
                                    'FILE_SAMPLE_1B.CSV'])
def test_accepts_exact_sample(name):
    check_sample(name, 1)


@pytest.mark.parametrize('member', ['../escape.csv', '/escape.csv',
                                     'nested/file.csv', 'file_sample_20.csv'])
def test_archive_rejects_wrong_or_unsafe_members(tmp_path, member):
    path = tmp_path / 'input.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(member, 'DESYNPUF_ID\na\n')
    with pytest.raises(ValueError):
        archive_members(path, spec())
    assert not (tmp_path.parent / 'escape.csv').exists()


class Response:
    def __init__(self, content, url, declared_size=None):
        self.content, self.url = content, url
        self.headers = {'Content-Length': str(declared_size if declared_size is not None else len(content))}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def raise_for_status(self):
        pass
    def iter_content(self, chunk_size):
        yield self.content


class Session:
    def __init__(self, response):
        self.response, self.calls = response, 0
    def get(self, *args, **kwargs):
        self.calls += 1
        return self.response


def zip_bytes(tmp_path, header='DESYNPUF_ID,CLM_ID\na,b\n'):
    path = tmp_path / 'source.zip'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(spec()['filename'][:-4] + '.csv', header)
    return path.read_bytes()


def test_roundtrip_cached_run_and_corruption_detection(tmp_path):
    item = spec()
    session = Session(Response(zip_bytes(tmp_path), item['url']))
    rows = {}
    path, row = fetch(session, item, tmp_path, rows)
    rows[row['path']] = row
    extract(path, item, tmp_path, rows, row)
    target = tmp_path / 'data/extracted/sample_1' / (item['filename'][:-4] + '.csv')
    assert target.read_text() == 'DESYNPUF_ID,CLM_ID\na,b\n'
    original_rows = {key: dict(value) for key, value in rows.items()}
    fetch(session, item, tmp_path, rows, verify_only=True)
    extract(path, item, tmp_path, rows, row, verify_only=True)
    assert rows == original_rows and session.calls == 1
    target.write_text('DESYNPUF_ID,CLM_ID\nz,b\n')  # same size, changed bytes
    with pytest.raises(ValueError, match='SHA-256 mismatch'):
        extract(path, item, tmp_path, rows, row, verify_only=True)


def test_rejects_truncated_download_and_removes_partial(tmp_path):
    item = spec()
    session = Session(Response(b'not-a-complete-zip', item['url'], 100))
    with pytest.raises(ValueError, match='Incomplete response'):
        fetch(session, item, tmp_path, {})
    assert not list((tmp_path / 'data/raw').glob('*'))


def test_rejects_wrong_sample_redirect(tmp_path):
    item = spec()
    session = Session(Response(b'', item['url'].replace('_1.zip', '_20.zip')))
    with pytest.raises(ValueError, match='Wrong sample'):
        fetch(session, item, tmp_path, {})


def test_rejects_html_as_pdf(tmp_path):
    item = dict(filename='guide.pdf', url='https://example.test/guide',
                sample_id='', file_type='guide', kind='pdf')
    with pytest.raises(ValueError, match='Expected PDF'):
        fetch(Session(Response(b'<html>error</html>', item['url'])), item, tmp_path, {})


def test_rejects_bad_claims_header(tmp_path):
    item = spec()
    session = Session(Response(zip_bytes(tmp_path, 'wrong,header\na,b\n'), item['url']))
    path, row = fetch(session, item, tmp_path, {})
    with pytest.raises(ValueError, match='Invalid claims CSV header'):
        extract(path, item, tmp_path, {}, row)


def test_reference_codes_are_exact_historical_office_set():
    path = Path(__file__).resolve().parents[1] / 'data/reference/em_office_visit_codes.csv'
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    expected = set(map(str, [*range(99201, 99206), *range(99211, 99216)]))
    assert {row['hcpcs_cd'] for row in rows} == expected
    assert len(rows) == 10
