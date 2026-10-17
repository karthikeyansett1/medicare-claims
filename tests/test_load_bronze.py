"""Loader preflight checks; PostgreSQL tests use isolated disposable schemas."""
from dataclasses import replace
import csv
import json
import os
from pathlib import Path
import uuid

import psycopg
from psycopg import sql
import pytest

from ingest.db import get_conn
from ingest.download import sha256
from ingest.load_bronze import SourceFile, TABLES, build_plan, header_of, load_plan, reconcile


def make_source(tmp_path, name='first.csv', table='beneficiary', year=2008,
                rows=(('000001',''),('000002',' NA '))):
    path=tmp_path/name
    with path.open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['DESYNPUF_ID','RAW_VALUE']);writer.writerows(rows)
    return SourceFile(path,table,1,year,('desynpuf_id','raw_value'),len(rows),sha256(path))


@pytest.mark.parametrize('header',['ID,id\n','ID,_sample_id\n','ID, ID2\n',''])
def test_rejects_colliding_or_unsafe_headers(tmp_path,header):
    path=tmp_path/'bad.csv';path.write_text(header)
    with pytest.raises(ValueError):header_of(path)


def test_preflight_rejects_missing_file_types(tmp_path):
    profile=tmp_path/'profile.json';profile.write_text(json.dumps({'files':{}}))
    with pytest.raises(ValueError,match='eight'):
        build_plan(tmp_path,tmp_path,profile,tmp_path/'manifest.csv')


def test_preflight_rejects_changed_source(tmp_path):
    source=make_source(tmp_path)
    directory=tmp_path/'data'/'sample_1';directory.mkdir(parents=True)
    destination=directory/source.path.name;source.path.replace(destination)
    key=destination.relative_to(tmp_path).as_posix()
    files={kind:dict(file=destination.name,columns=['DESYNPUF_ID','RAW_VALUE'],rows=2,
                    cms_expected_rows=2,cms_row_count_matches=True) for kind in TABLES}
    profile=tmp_path/'profile.json'
    profile.write_text(json.dumps({'sample':1,'files':files,'input_sha256':{key:source.sha256}}))
    manifest=tmp_path/'manifest.csv'
    with manifest.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['path','sha256','size_bytes','sample_id','file_type'])
        writer.writeheader();writer.writerow(dict(path=key,sha256=source.sha256,size_bytes=destination.stat().st_size,
                                                 sample_id=1,file_type='beneficiary_2008'))
    content=destination.read_bytes().replace(b'000001',b'000009');destination.write_bytes(content)
    with pytest.raises(ValueError,match='SHA-256 mismatch'):
        build_plan(tmp_path,tmp_path/'data',profile,manifest)


@pytest.fixture
def database():
    if os.getenv('RUN_DB_TESTS')!='1':pytest.skip('Set RUN_DB_TESTS=1 for isolated PostgreSQL tests')
    schema='test_bronze_'+uuid.uuid4().hex[:12]
    conn=get_conn();conn.autocommit=True
    try:
        yield conn,schema
    finally:
        conn.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))
        conn.close()


def test_db_preserves_text_lineage_and_reloads_without_duplicates(tmp_path,database):
    conn,schema=database
    first=make_source(tmp_path)
    second=make_source(tmp_path,name='second.csv',year=2009,rows=(('000003','not-a-date'),))
    one=load_plan(conn,[first,second],schema)
    two=load_plan(conn,[first,second],schema)
    assert one['total_loaded_rows']==two['total_loaded_rows']==3
    rows=conn.execute(sql.SQL('SELECT desynpuf_id,raw_value,_sample_id,_file_year,_source_file FROM {} ORDER BY desynpuf_id').format(sql.Identifier(schema,'beneficiary'))).fetchall()
    assert rows==[('000001','',1,2008,'first.csv'),('000002',' NA ',1,2008,'first.csv'),('000003','not-a-date',1,2009,'second.csv')]
    assert reconcile(conn,[first,second],schema)['all_counts_match']


def test_db_copy_failure_rolls_back_all_tables(tmp_path,database):
    conn,schema=database
    first=make_source(tmp_path)
    second=make_source(tmp_path,name='second.csv',table='carrier',year=None)
    load_plan(conn,[first,second],schema)
    changed=make_source(tmp_path,name='changed.csv',rows=(('009999','new data'),))
    bad=make_source(tmp_path,name='bad.csv',table='carrier',year=None)
    bad.path.write_text('DESYNPUF_ID,RAW_VALUE\nx,y,unexpected_extra_field\n')
    bad=replace(bad,sha256=sha256(bad.path),expected_rows=1)
    with pytest.raises(psycopg.errors.BadCopyFileFormat):
        load_plan(conn,[changed,bad],schema)
    result=reconcile(conn,[first,second],schema)
    assert result['total_loaded_rows']==4


def test_db_count_mismatch_rolls_back(tmp_path,database):
    conn,schema=database
    source=make_source(tmp_path);load_plan(conn,[source],schema)
    with pytest.raises(ValueError,match='row count mismatch'):
        load_plan(conn,[replace(source,expected_rows=3)],schema)
    assert reconcile(conn,[source],schema)['total_loaded_rows']==2


def test_db_financial_mismatch_rolls_back(tmp_path,database):
    conn,schema=database
    source=make_source(tmp_path,rows=(('000001','0.10'),('000002','-0.20')))
    source=replace(source,money_totals={'raw_value':-10})
    load_plan(conn,[source],schema)
    with pytest.raises(ValueError,match='Financial source totals differ'):
        load_plan(conn,[replace(source,money_totals={'raw_value':10})],schema)
    assert reconcile(conn,[source],schema)['files'][0]['money_totals_cents']=={'raw_value':-10}


def test_db_existing_schema_mismatch_does_not_destroy_table(tmp_path,database):
    conn,schema=database
    source=make_source(tmp_path);load_plan(conn,[source],schema)
    conn.execute(sql.SQL('ALTER TABLE {} ADD COLUMN unexpected TEXT').format(sql.Identifier(schema,'beneficiary')))
    with pytest.raises(ValueError,match='Unexpected table schema'):
        load_plan(conn,[source],schema)
    assert conn.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(schema,'beneficiary'))).fetchone()[0]==2


def test_db_streamed_hash_mismatch_rolls_back(tmp_path,database):
    conn,schema=database
    source=make_source(tmp_path);load_plan(conn,[source],schema)
    with pytest.raises(ValueError,match='Source changed during COPY'):
        load_plan(conn,[replace(source,sha256='0'*64)],schema)
    assert reconcile(conn,[source],schema)['total_loaded_rows']==2


def test_cross_sample_columns_fail_before_connection_access(tmp_path):
    first = make_source(tmp_path)
    second = replace(make_source(tmp_path, name='sample2.csv'), sample=2,
                     columns=('desynpuf_id', 'different'))
    with pytest.raises(ValueError, match='Cross-sample column mismatch'):
        load_plan(None, [first, second])


def test_db_combined_samples_retain_colliding_ids_and_rollback(tmp_path, database):
    conn, schema = database
    first = make_source(tmp_path)
    second = replace(make_source(tmp_path, name='sample2.csv'), sample=2)
    result = load_plan(conn, [first, second], schema)
    assert result['total_loaded_rows'] == 4
    assert {f['sample_id'] for f in result['files']} == {1, 2}
    rows = conn.execute(sql.SQL('select _sample_id,count(*) from {} group by 1 order by 1').format(
        sql.Identifier(schema, 'beneficiary'))).fetchall()
    assert rows == [(1, 2), (2, 2)]
    with pytest.raises(ValueError, match='row count mismatch'):
        load_plan(conn, [first, replace(second, expected_rows=3)], schema)
    assert reconcile(conn, [first, second], schema)['total_loaded_rows'] == 4


def test_preflight_rejects_profile_sample_mismatch(tmp_path):
    profile = tmp_path / 'profile.json'
    profile.write_text(json.dumps({'sample': 2, 'files': dict.fromkeys(TABLES, {})}))
    with pytest.raises(ValueError, match='Profile sample metadata'):
        build_plan(tmp_path, tmp_path, profile, tmp_path / 'manifest.csv', expected_sample=1)
