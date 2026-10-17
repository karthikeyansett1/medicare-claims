"""Regression cases for misleading claims profiles and chunk-boundary errors."""
import csv
import sqlite3

import pandas as pd

from ingest.profile_raw import cents, facility_stats, init_db, parse_dates, profile_file


def test_calendar_dates_require_eight_digits_and_valid_calendar():
    values = pd.Series(['20080229','20090229','20091301','2009011','','20090101'])
    parsed = parse_dates(values)
    assert parsed.notna().tolist() == [True,False,False,False,False,True]


def test_money_has_exact_cents_and_reports_malformed_tokens():
    values = cents(pd.Series(['0.10','0.20','-12.34','1.2','0','','NA','1.001']))
    assert values.iloc[:5].tolist() == [10,20,-1234,120,0]
    assert values.iloc[5:].isna().all()
    assert values.sum() == -1084


def write_csv(path, rows):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def run_profile(path, kind, known, deaths=None, chunksize=1):
    conn=sqlite3.connect(':memory:');init_db(conn)
    result=profile_file(path,kind,conn,known,deaths or {},{'4280'},chunksize)
    return result,conn


def test_carrier_paid_slots_missing_hcpcs_and_blank_provider(tmp_path):
    row={'DESYNPUF_ID':'m','CLM_ID':'c','CLM_FROM_DT':'20090102','CLM_THRU_DT':'20090103',
         'ICD9_DGNS_CD_1':'428.0','ICD9_DGNS_CD_2':'BAD'}
    for n in range(1,14):
        for prefix in ['HCPCS_CD','PRF_PHYSN_NPI','LINE_ICD9_DGNS_CD','LINE_NCH_PMT_AMT','LINE_ALOWD_CHRG_AMT']:
            row[f'{prefix}_{n}']=''
    row.update(LINE_NCH_PMT_AMT_1='12.34', LINE_ALOWD_CHRG_AMT_1='20',
               HCPCS_CD_2='99213', LINE_NCH_PMT_AMT_2='0.10', LINE_ALOWD_CHRG_AMT_2='0.20',
               PRF_PHYSN_NPI_2='npi', LINE_ICD9_DGNS_CD_2='4280')
    path=tmp_path/'carrier.csv';write_csv(path,[row,row])
    result,conn=run_profile(path,'carrier_a',{'m'},{'m':pd.Timestamp('20090101')})
    try:
        assert result['rows']==2 and result['distinct_event_ids']==1
        assert result['duplicate_event_id_excess_rows']==1
        q=result['quirks']
        assert q['possible_line_slots']==26 and q['active_line_slots']==4
        assert q['active_missing_hcpcs']==2 and q['active_missing_npi']==2
        assert q['hcpcs_present_missing_npi']==0
        assert q['paid_cents_missing_hcpcs']==2468
        assert q['paid_cents_hcpcs_present']==20
        assert q['service_start_after_death']==2
        assert result['diagnosis']['claim']['unmatched_occurrences']==2
        assert result['diagnosis']['claim']['dotted_occurrences']==2
    finally:conn.close()


def test_facility_repeated_and_differing_payments_cross_chunks(tmp_path):
    template=dict(DESYNPUF_ID='m',CLM_ID='a',SEGMENT='1',CLM_FROM_DT='20090101',
                  CLM_THRU_DT='20090103',PRVDR_NUM='001234',CLM_PMT_AMT='100.10',
                  CLM_ADMSN_DT='20090101',NCH_BENE_DSCHRG_DT='20090103',ICD9_DGNS_CD_1='4280')
    rows=[template,dict(template,SEGMENT='2'),dict(template,CLM_ID='b'),
          dict(template,CLM_ID='b',SEGMENT='2',CLM_PMT_AMT='200.10')]
    path=tmp_path/'ip.csv';write_csv(path,rows)
    small,c1=run_profile(path,'inpatient',{'m'},chunksize=1)
    large,c2=run_profile(path,'inpatient',{'m'},chunksize=10)
    try:
        assert small==large
        stats=facility_stats(c1,'inpatient')
        assert stats==facility_stats(c2,'inpatient')
        assert stats['multirow_claim_groups']==2
        assert stats['repeated_equal_payment_groups']==1
        assert stats['differing_payment_groups']==1
        assert stats['repeat_payment_excess_cents']==10010
        assert stats['duplicate_segment_key_excess_rows']==0
        assert stats['candidate_stay_keys_with_multiple_claim_ids']==1
        assert small['money']['CLM_PMT_AMT']['total_cents']==50040
    finally:c1.close();c2.close()


def test_null_tokens_and_negative_gross_drug_cost_are_not_silently_cleaned(tmp_path):
    rows=[dict(DESYNPUF_ID='NA',PDE_ID='p1',SRVC_DT='20090229',PROD_SRVC_ID='',
               TOT_RX_CST_AMT='-1.23',PTNT_PAY_AMT='bad'),
          dict(DESYNPUF_ID='orphan',PDE_ID='p2',SRVC_DT='20090101',PROD_SRVC_ID='000123',
               TOT_RX_CST_AMT='',PTNT_PAY_AMT='0')]
    path=tmp_path/'pde.csv';write_csv(path,rows)
    result,conn=run_profile(path,'pde',{'NA'})
    try:
        assert result['null_counts']['DESYNPUF_ID']==0
        assert result['null_counts']['PROD_SRVC_ID']==1
        assert result['dates']['SRVC_DT']['invalid']==1
        assert result['quirks']['orphan_member_rows']==1
        assert result['money']['TOT_RX_CST_AMT']==dict(total_cents=-123,negative=1,invalid=0,blank=1)
        assert result['money']['PTNT_PAY_AMT']['invalid']==1
    finally:conn.close()
