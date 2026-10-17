"""Public snapshot and dashboard measure contract tests."""
import json
import os
import hashlib
import pandas as pd
import pytest
from dashboard.data import ROOT, load_data, scoped, aggregate, FORBIDDEN


def test_weighted_ratios_and_empty():
    f=pd.DataFrame({'panel_size':[20,40],'medical_paid_amt':[120,2400],'member_months':[12,120], 'admissions':[1,4], 'ed_claim_count':[2,6], 'readmissions':[1,2], 'index_stays':[2,20]})
    a=aggregate(f)
    assert a['Medical PMPM']==2520/132
    assert a['30-day readmissions']==3/22
    assert a['Admissions / 1,000']==5/132*12000
    assert aggregate(f.iloc[:0])['Medical PMPM'] is None


def test_public_snapshot_contract():
    frames,manifest=load_data()
    for frame in frames.values():
        assert not FORBIDDEN.intersection(frame.columns)
    assert frames['providers'].panel_size.ge(20).all()
    expected_samples = {1} if os.getenv('FIXTURE_MANIFEST') else {1,2}
    assert len(frames['overview'])==4*len(expected_samples)
    assert set(manifest['samples'])==expected_samples
    assert '_sample_id' not in frames['conditions']
    assert frames['providers'].attributed_npi.dtype.name=='string'
    assert frames['providers'].attributed_npi.str.startswith('0').any()
    assert scoped(frames['providers'],99,2009).empty
    for sample in expected_samples:
        for year in (2009,2010):
            for method in ('A_visits','B_allowed'):
                overview=scoped(frames['overview'],sample,year,method)
                providers=scoped(frames['providers'],sample,year,method)
                assert overview.panel_size.sum()>providers.panel_size.sum()
                coverage=scoped(frames['coverage'],sample,year).iloc[0]
                assert overview.panel_size.sum()==coverage['attributed_a' if method=='A_visits' else 'attributed_b']


def test_checksum_rejects_tampering(tmp_path):
    (tmp_path/'x.csv').write_text('attributed_npi\n0123456789\n')
    (tmp_path/'manifest.json').write_text(json.dumps({'files':{'providers':{'file':'x.csv','sha256':'wrong'}}}))
    with pytest.raises(ValueError,match='checksum'): load_data(tmp_path)


def test_identifier_privacy(tmp_path):
    content=b'member_id\n123\n'
    (tmp_path/'x.csv').write_bytes(content)
    (tmp_path/'manifest.json').write_text(json.dumps({'files':{'providers':{'file':'x.csv','sha256':hashlib.sha256(content).hexdigest()}}}))
    with pytest.raises(ValueError,match='identifiers'): load_data(tmp_path)


@pytest.mark.skipif(os.getenv('RUN_DB_TESTS')!='1',reason='requires warehouse')
def test_export_totals_against_warehouse():
    from ingest.db import get_conn
    frames,_=load_data()
    with get_conn() as conn:
        for row in frames['overview'].itertuples(index=False,name=None):
            sample,year,method,*values=row
            actual=conn.execute('''select sum(panel_size),sum(member_months),sum(medical_paid_amt),sum(rx_gross_cost_amt),sum(ed_claim_count),sum(admissions),sum(expected_medical_paid_amt),sum(index_stays),sum(readmissions) from marts.mart_provider_performance where _sample_id=%s and year=%s and method=%s''',(sample,year,method)).fetchone()
            assert [float(v or 0) for v in actual]==pytest.approx(values,rel=1e-10)


def test_four_pages_and_filter_controls():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/'dashboard/app.py'),default_timeout=20).run()
    assert not app.exception
    app.sidebar.radio[0].set_value('Provider scorecard').run()
    app.text_input[0].set_value('no-provider').run()
    assert any('No providers' in item.value for item in app.info)
    app.sidebar.radio[0].set_value('Method comparison').run()
    app.select_slider[0].set_value(30).run()
    assert not app.exception
    app.sidebar.radio[0].set_value('Conditions').run()
    assert app.sidebar.selectbox[0].disabled
    assert app.sidebar.selectbox[2].disabled
    assert any('pool all loaded samples' in item.value for item in app.info)
    assert not app.exception
