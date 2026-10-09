"""Profile verified Sample 1 CSVs without changing or loading source data.

Pandas reads bounded chunks. SQLite on temporary disk keeps exact event-key and
facility-segment statistics across chunks. Money is accumulated as integer cents.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import time

import pandas as pd
import yaml

from ingest.download import ROOT, read_manifest, verify_record

EXPECTED_SAMPLE_1 = dict(beneficiary_2008=116352, beneficiary_2009=114538,
    beneficiary_2010=112754, inpatient=66773, outpatient=790790,
    carrier_a=2370667, carrier_b=2370668, pde=5552421)
COVERAGE = ['BENE_HI_CVRAGE_TOT_MONS', 'BENE_SMI_CVRAGE_TOT_MONS',
            'BENE_HMO_CVRAGE_TOT_MONS', 'PLAN_CVRG_MOS_NUM']
CHRONIC = ['SP_ALZHDMTA', 'SP_CHF', 'SP_CHRNKIDN', 'SP_CNCR', 'SP_COPD',
           'SP_DEPRESSN', 'SP_DIABETES', 'SP_ISCHMCHT', 'SP_OSTEOPRS', 'SP_RA_OA', 'SP_STRKETIA']


def parse_dates(values):
    shaped = values.str.fullmatch(r'\d{8}')
    return pd.to_datetime(values.where(shaped), format='%Y%m%d', errors='coerce')


def cents(values):
    # Convert each distinct token once, without binary floating-point rounding.
    mapping = {token: int(Decimal(token) * 100) if re.fullmatch(r'-?\d+(?:\.\d{1,2})?', token)
               else None for token in values.unique()}
    return values.map(mapping).astype('Int64')


def init_db(conn):
    conn.executescript('''
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA cache_size=-32768;
        PRAGMA temp_store=FILE;
        CREATE TABLE ids(scope TEXT, value TEXT, PRIMARY KEY(scope,value)) WITHOUT ROWID;
        CREATE TABLE facility(kind TEXT, member TEXT, claim TEXT, segment TEXT,
            paid INTEGER, admit TEXT, discharge TEXT, provider TEXT, principal_dx TEXT);
    ''')


def load_ccs(path):
    with path.open(newline='') as stream:
        reader = csv.reader(stream)
        next(reader); next(reader)
        return {row[0].strip(" '") for row in reader if row[0].strip(" '")}


def beneficiary_context(paths):
    """Use earliest observed valid death date, reporting inconsistent values."""
    all_ids, death_values = set(), {}
    for path in paths:
        for chunk in pd.read_csv(path, dtype=str, keep_default_na=False, chunksize=50000,
                                 usecols=['DESYNPUF_ID', 'BENE_DEATH_DT']):
            all_ids.update(chunk.DESYNPUF_ID.str.strip())
            parsed = parse_dates(chunk.BENE_DEATH_DT.str.strip())
            for member, death in zip(chunk.DESYNPUF_ID.str.strip()[parsed.notna()], parsed.dropna()):
                death_values.setdefault(member, set()).add(death)
    return all_ids, {member: min(dates) for member, dates in death_values.items()}, sum(
        len(dates) > 1 for dates in death_values.values())


def profile_file(path, kind, conn, known_members, deaths, ccs_codes, chunksize=50000):
    result = dict(file=path.name, rows=0, columns=[], null_counts=Counter(),
                  distinct_members=0, dates={}, money={}, quirks=Counter(),
                  diagnosis={}, enrollment=Counter(), distributions={})
    member_ids, dx_counts, unmatched = set(), {}, {}
    for chunk_index, chunk in enumerate(pd.read_csv(path, dtype=str, keep_default_na=False,
                                                   chunksize=chunksize)):
        chunk = chunk.apply(lambda col: col.str.strip())
        result['columns'] = list(chunk.columns)
        result['rows'] += len(chunk)
        result['null_counts'].update({col: int(value) for col, value in chunk.eq('').sum().items()})
        ids = chunk.DESYNPUF_ID
        member_ids.update(ids[ids.ne('')])
        result['quirks']['orphan_member_rows'] += int((~ids.isin(known_members)).sum())
        event_key = 'CLM_ID' if 'CLM_ID' in chunk else 'PDE_ID' if 'PDE_ID' in chunk else 'DESYNPUF_ID'
        keys = chunk[event_key]
        conn.executemany('INSERT OR IGNORE INTO ids VALUES (?,?)',
                         ((kind, key) for key in keys if key))
        parsed_dates = {}
        for col in [c for c in chunk if c.endswith('_DT')]:
            parsed = parse_dates(chunk[col]); parsed_dates[col] = parsed
            valid = parsed.dropna()
            info = result['dates'].setdefault(col, dict(nonblank=0, invalid=0, minimum=None, maximum=None))
            info['nonblank'] += int(chunk[col].ne('').sum())
            info['invalid'] += int((chunk[col].ne('') & parsed.isna()).sum())
            if not valid.empty:
                low, high = valid.min().strftime('%Y-%m-%d'), valid.max().strftime('%Y-%m-%d')
                info['minimum'] = min(info['minimum'] or low, low)
                info['maximum'] = max(info['maximum'] or high, high)
        q = result['quirks']
        for start, end, label in [('CLM_FROM_DT','CLM_THRU_DT','claim_end_before_start'),
                                 ('CLM_ADMSN_DT','NCH_BENE_DSCHRG_DT','discharge_before_admission')]:
            if start in parsed_dates and end in parsed_dates:
                q[label] += int((parsed_dates[end] < parsed_dates[start]).sum())
        service_col = ('CLM_ADMSN_DT' if kind == 'inpatient' else
                       'SRVC_DT' if kind == 'pde' else 'CLM_FROM_DT')
        if service_col in parsed_dates:
            death = pd.to_datetime(ids.map(deaths))
            q['rows_with_known_death'] += int(death.notna().sum())
            q['service_start_after_death'] += int((parsed_dates[service_col] > death).sum())
            q['service_start_outside_2008_2010'] += int((parsed_dates[service_col].notna() &
                ~parsed_dates[service_col].dt.year.between(2008,2010)).sum())
            if 'CLM_THRU_DT' in parsed_dates:
                q['claim_end_after_death'] += int((parsed_dates['CLM_THRU_DT'] > death).sum())
        money_cols = [c for c in chunk if c in ['CLM_PMT_AMT','TOT_RX_CST_AMT','PTNT_PAY_AMT']
                      or c.startswith(('LINE_NCH_PMT_AMT_', 'LINE_ALOWD_CHRG_AMT_'))]
        numeric = {}
        for col in money_cols:
            values = cents(chunk[col]); numeric[col] = values
            info = result['money'].setdefault(col, dict(total_cents=0, negative=0, invalid=0, blank=0))
            info['total_cents'] += int(values.sum())
            info['negative'] += int(values.lt(0).sum())
            info['invalid'] += int((chunk[col].ne('') & values.isna()).sum())
            info['blank'] += int(chunk[col].eq('').sum())
        groups = {'claim': [c for c in chunk if c.startswith('ICD9_DGNS_CD_')],
                  'line': [c for c in chunk if c.startswith('LINE_ICD9_DGNS_CD_')],
                  'admitting': [c for c in chunk if c == 'ADMTNG_ICD9_DGNS_CD']}
        for group, columns in groups.items():
            if not columns:
                continue
            counts = dx_counts.setdefault(group, Counter())
            bad = unmatched.setdefault(group, Counter())
            info = result['diagnosis'].setdefault(group, dict(nonblank_occurrences=0,
                                                            dotted_occurrences=0))
            for col in columns:
                values = chunk[col][chunk[col].ne('')]
                info['nonblank_occurrences'] += len(values)
                info['dotted_occurrences'] += int(values.str.contains('.', regex=False).sum())
                normalized = values.str.upper().str.replace('.', '', regex=False)
                vc = normalized.value_counts()
                counts.update({str(k): int(v) for k,v in vc.items()})
                bad.update({str(k): int(v) for k,v in vc.items() if k not in ccs_codes})
        if kind.startswith('carrier'):
            for n in range(1,14):
                hcpcs, npi, dx = (chunk[f'{prefix}_{n}'] for prefix in
                                  ['HCPCS_CD','PRF_PHYSN_NPI','LINE_ICD9_DGNS_CD'])
                paid, allowed = numeric[f'LINE_NCH_PMT_AMT_{n}'], numeric[f'LINE_ALOWD_CHRG_AMT_{n}']
                has_code = hcpcs.ne('')
                active = has_code | npi.ne('') | dx.ne('') | paid.fillna(0).ne(0) | allowed.fillna(0).ne(0)
                q['possible_line_slots'] += len(chunk)
                q['active_line_slots'] += int(active.sum())
                q['hcpcs_present_lines'] += int(has_code.sum())
                q['hcpcs_present_missing_npi'] += int((has_code & npi.eq('')).sum())
                q['active_missing_npi'] += int((active & npi.eq('')).sum())
                q['active_missing_hcpcs'] += int((active & ~has_code).sum())
                q['nonzero_paid_missing_hcpcs'] += int((paid.fillna(0).ne(0) & ~has_code).sum())
                q['paid_cents_missing_hcpcs'] += int(paid[~has_code].sum())
                q['paid_cents_hcpcs_present'] += int(paid[has_code].sum())
                q['paid_above_allowed_lines'] += int((paid > allowed).sum())
        if kind in ('inpatient','outpatient'):
            result['distributions'].setdefault('SEGMENT', Counter()).update(chunk.SEGMENT.value_counts().to_dict())
            def col(name):
                return chunk[name] if name in chunk else [''] * len(chunk)
            conn.executemany('INSERT INTO facility VALUES (?,?,?,?,?,?,?,?,?)',
                ((kind,m,c,s,None if pd.isna(p) else int(p),a,d,f,dx)
                 for m,c,s,p,a,d,f,dx in zip(ids,chunk.CLM_ID,chunk.SEGMENT,numeric['CLM_PMT_AMT'],
                    col('CLM_ADMSN_DT'),col('NCH_BENE_DSCHRG_DT'),chunk.PRVDR_NUM,chunk.ICD9_DGNS_CD_1)))
        if kind.startswith('beneficiary'):
            coverage = {c: pd.to_numeric(chunk[c],errors='coerce') for c in COVERAGE}
            for col, values in coverage.items():
                result['enrollment'][col+'_invalid'] += int((~values.between(0,12) | values.mod(1).ne(0)).sum())
                result['distributions'].setdefault(col,Counter()).update(chunk[col].value_counts().to_dict())
            result['enrollment']['hmo_positive'] += int(coverage['BENE_HMO_CVRAGE_TOT_MONS'].gt(0).sum())
            full = coverage[COVERAGE[0]].eq(12) & coverage[COVERAGE[1]].eq(12) & coverage[COVERAGE[2]].eq(0)
            result['enrollment']['a12_b12_hmo0'] += int(full.sum())
            for col in CHRONIC:
                result['enrollment']['invalid_chronic_flag_cells'] += int((~chunk[col].isin(['1','2'])).sum())
            result['quirks']['death_before_birth'] += int((parsed_dates['BENE_DEATH_DT'] < parsed_dates['BENE_BIRTH_DT']).sum())
        conn.commit()
        if (chunk_index+1) % 10 == 0:
            print(f'  {kind}: {result["rows"]:,} rows', flush=True)
    result['distinct_members'] = len(member_ids)
    result['event_key'] = event_key
    result['distinct_event_ids'] = conn.execute('SELECT COUNT(*) FROM ids WHERE scope=?',(kind,)).fetchone()[0]
    result['duplicate_event_id_excess_rows'] = result['rows'] - result['null_counts'][event_key] - result['distinct_event_ids']
    for group, counts in dx_counts.items():
        result['diagnosis'][group].update(distinct_codes=len(counts),
            unmatched_occurrences=sum(unmatched[group].values()), distinct_unmatched_codes=len(unmatched[group]),
            unmatched_codes=dict(sorted(unmatched[group].items())))
    result['null_rates'] = {c: n/result['rows'] if result['rows'] else None for c,n in result['null_counts'].items()}
    return result


def facility_stats(conn, kind):
    groups = '''SELECT member,claim,COUNT(*) n,COUNT(DISTINCT segment) segments,
        COUNT(paid) known_paid,COUNT(DISTINCT paid) paid_values,MAX(paid) paid,
        COUNT(DISTINCT admit) admits,COUNT(DISTINCT discharge) discharges,
        COUNT(DISTINCT provider) providers,COUNT(DISTINCT principal_dx) diagnoses
        FROM facility WHERE kind=? GROUP BY member,claim'''
    result = dict(claim_groups=0, multirow_claim_groups=0, duplicate_segment_key_excess_rows=0,
                  repeated_equal_payment_groups=0, differing_payment_groups=0,
                  missing_payment_groups=0, repeat_payment_excess_cents=0,
                  differing_header_groups=0, differing_admission_groups=0,
                  differing_discharge_groups=0, differing_provider_groups=0,
                  differing_principal_diagnosis_groups=0,
                  repeated_equal_nonzero_payment_groups=0)
    for row in conn.execute(groups,(kind,)):
        _,_,n,segments,known_paid,paid_values,paid,admits,discharges,providers,diagnoses=row
        result['claim_groups'] += 1
        result['duplicate_segment_key_excess_rows'] += n-segments
        if n > 1:
            result['multirow_claim_groups'] += 1
            if known_paid != n:
                result['missing_payment_groups'] += 1
            elif paid_values == 1:
                result['repeated_equal_payment_groups'] += 1
                result['repeated_equal_nonzero_payment_groups'] += int(paid != 0)
                result['repeat_payment_excess_cents'] += (n-1)*paid
            else:
                result['differing_payment_groups'] += 1
            result['differing_header_groups'] += int(max(admits,discharges,providers,diagnoses)>1)
            result['differing_admission_groups'] += int(admits > 1)
            result['differing_discharge_groups'] += int(discharges > 1)
            result['differing_provider_groups'] += int(providers > 1)
            result['differing_principal_diagnosis_groups'] += int(diagnoses > 1)
    if kind == 'inpatient':
        result['member_admit_facility_groups'] = conn.execute('''SELECT COUNT(*) FROM
            (SELECT member,admit,provider FROM facility WHERE kind=? GROUP BY member,admit,provider)''',(kind,)).fetchone()[0]
        result['candidate_stay_keys_with_multiple_claim_ids'] = conn.execute('''SELECT COUNT(*) FROM
            (SELECT 1 FROM facility WHERE kind=? GROUP BY member,admit,provider HAVING COUNT(DISTINCT claim)>1)''',(kind,)).fetchone()[0]
    return result


def render_report(report):
    files = report['files']
    lines = ['# Sample 1 raw data profile', '',
        'All eight source files were profiled in full without altering rows. This is a',
        'source inventory and methodology diagnostic, not a cleaned warehouse or a',
        'provider-performance result. Detailed counters and column null rates are in',
        '`data_profile.json`. Interpretation and source references are in',
        '[profiling decisions](profile_interpretation.md).', '',
        '## Source counts and keys', '',
        '| File type | Rows | CMS expected | Distinct members | Distinct event IDs | Duplicate ID excess rows |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for kind,info in files.items():
        lines.append(f"| {kind} | {info['rows']:,} | {info['cms_expected_rows']:,} | {info['distinct_members']:,} | {info['distinct_event_ids']:,} | {info['duplicate_event_id_excess_rows']:,} |")
    lines += ['', 'Event IDs are DESYNPUF_ID for beneficiary files, PDE_ID for drug events,',
        'and CLM_ID for claims. Repeated facility claim IDs can be segments, not duplicate claims.',
        f"Carrier A/B overlapping claim IDs: **{report['carrier_overlapping_ids']:,}**.", '',
        '## File grain and verified headers', '',
        '| File type | Observed source grain | Columns |', '| --- | --- | ---: |']
    for kind,info in files.items():
        grain = ('Beneficiary in one file year' if kind.startswith('beneficiary') else
                 'Claim segment; CLM_ID can repeat' if kind in ('inpatient','outpatient') else
                 'Professional claim with 13 wide line slots' if kind.startswith('carrier') else 'Prescription drug event')
        lines.append(f"| {kind} | {grain} | {len(info['columns'])} |")
    lines += ['', '## 1 Date fields', '', 'Dates require exactly eight digits and a valid calendar date.',
        'Blank values are counted separately; ranges exclude blanks and invalid dates.', '',
        '| File | Field | Nonblank | Invalid nonblank | Minimum | Maximum |', '| --- | --- | ---: | ---: | --- | --- |']
    for kind,info in files.items():
        for col,d in info['dates'].items():
            lines.append(f"| {kind} | {col} | {d['nonblank']:,} | {d['invalid']:,} | {d['minimum']} | {d['maximum']} |")
    lines += ['', '## 2 Carrier line structure and reconciliation', '',
        'An active slot has HCPCS, NPI, line diagnosis, nonzero paid, or nonzero allowed amount.',
        'This is a profiling definition, not the final model inclusion rule.', '',
        '| Check | Carrier A | Carrier B |', '| --- | ---: | ---: |']
    for label in ['possible_line_slots','active_line_slots','hcpcs_present_lines','active_missing_hcpcs',
                  'nonzero_paid_missing_hcpcs','paid_cents_missing_hcpcs','paid_cents_hcpcs_present']:
        lines.append(f"| {label} | {files['carrier_a']['quirks'][label]:,} | {files['carrier_b']['quirks'][label]:,} |")
    lines += ['', 'Cents counters are integer cents. Payments on missing-HCPCS slots must not',
        'silently disappear during the later unpivot.', '', '## 3 Facility claim segments', '',
        '| Check | Inpatient | Outpatient |', '| --- | ---: | ---: |']
    for label in ['claim_groups','multirow_claim_groups','duplicate_segment_key_excess_rows',
                  'repeated_equal_payment_groups','differing_payment_groups','missing_payment_groups',
                  'repeated_equal_nonzero_payment_groups','repeat_payment_excess_cents',
                  'differing_header_groups','differing_admission_groups','differing_discharge_groups',
                  'differing_provider_groups','differing_principal_diagnosis_groups']:
        outpatient = ('N/A' if label in ('differing_admission_groups','differing_discharge_groups')
                      else f"{report['segments']['outpatient'][label]:,}")
        lines.append(f"| {label} | {report['segments']['inpatient'][label]:,} | {outpatient} |")
    lines += ['', 'Equal payments across segments are a duplication diagnostic, not proof that',
        'every repeated amount should be deleted. Differing-payment groups require explicit policy.',
        f"Inpatient candidate (member, admission, facility) groups: {report['segments']['inpatient']['member_admit_facility_groups']:,}; keys containing multiple claim IDs: {report['segments']['inpatient']['candidate_stay_keys_with_multiple_claim_ids']:,}.", '',
        '## 4 Diagnosis format and CCS coverage', '',
        'Counts are diagnosis-position occurrences, not people. Claim, admitting, and line',
        'diagnoses are separate scopes. Match uses trimmed uppercase codes without decimals.', '',
        '| File | Scope | Nonblank | With decimal | Unmatched occurrences | Distinct unmatched codes |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for kind,info in files.items():
        for group,d in info['diagnosis'].items():
            lines.append(f"| {kind} | {group} | {d['nonblank_occurrences']:,} | {d['dotted_occurrences']:,} | {d['unmatched_occurrences']:,} | {d['distinct_unmatched_codes']:,} |")
    lines += ['', 'The JSON includes each unmatched code and its occurrence count. No codes were dropped.', '',
        '## 5 Missing rendering NPIs', '', '| Scope | Carrier A | Carrier B |', '| --- | ---: | ---: |']
    for label in ['active_missing_npi','hcpcs_present_missing_npi']:
        lines.append(f"| {label} | {files['carrier_a']['quirks'][label]:,} | {files['carrier_b']['quirks'][label]:,} |")
    lines += ['', 'Blank rendering NPIs prevent provider attribution for those slots; zero-paid',
        'empty slots are not counted as active solely because the payment field is populated.', '',
        '## 6 Synthetic temporal and linkage anomalies', '',
        'Death date is the earliest valid nonblank value across all three beneficiary files.',
        f"Members with conflicting nonblank death dates: {report['conflicting_death_dates']:,}.",
        'Start means admission for inpatient, claim-from for outpatient/carrier, and service',
        'date for PDE. End-after-death can reflect billing timing and is reported separately.', '',
        '| File | Orphan member rows | Known-death rows | Start after death | End after death | End before start | Discharge before admission |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for kind,info in files.items():
        if kind.startswith('beneficiary'):
            continue
        q=info['quirks']
        lines.append('| '+kind+' | '+' | '.join(f"{q.get(key,0):,}" for key in ['orphan_member_rows','rows_with_known_death','service_start_after_death','claim_end_after_death','claim_end_before_start','discharge_before_admission'])+' |')
    lines += ['', 'Facility start dates can precede 2008 while the claim ends during the study',
        'period. These rows remain in the source baseline; they are not automatically invalid.',
        f"Start dates outside 2008–2010: inpatient {files['inpatient']['quirks']['service_start_outside_2008_2010']:,}; outpatient {files['outpatient']['quirks']['service_start_outside_2008_2010']:,}.",
        'Discharge-before-admission applies only to inpatient; other file types have no',
        'admission/discharge pair and their zero counter means the check is not applicable.']
    lines += ['', '## 7 Financial amounts', '',
        'Raw facility sums include all segments and are not yet deduplicated. Carrier sums',
        'include all 13 slots. PDE gross drug cost and patient pay remain separate from',
        'Medicare medical payments. Null or malformed amounts do not become zero silently;',
        'the table totals valid amounts and reports invalid counts.', '',
        '| File | Amount | Total dollars | Negative values | Invalid nonblank | Blank |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for kind,info in files.items():
        totals = {}
        for col,d in info['money'].items():
            label = re.sub(r'_\d+$','',col)
            aggregate=totals.setdefault(label,Counter());aggregate.update(d)
        for label,d in totals.items():
            lines.append(f"| {kind} | {label} | {Decimal(d['total_cents'])/100:,.2f} | {d['negative']:,} | {d['invalid']:,} | {d['blank']:,} |")
    lines += ['', '## 8 Enrollment and chronic flags', '',
        'The screening count below uses exactly A=12, B=12, HMO=0. It is not the final',
        'eligible population: enrollment through death and measure-specific windows are undecided.', '',
        '| Year | Member rows | HMO months above zero | A12 B12 HMO0 | Invalid month cells | Invalid chronic flag cells |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for kind,info in files.items():
        if not kind.startswith('beneficiary'):continue
        e=info['enrollment']
        lines.append(f"| {kind[-4:]} | {info['rows']:,} | {e['hmo_positive']:,} | {e['a12_b12_hmo0']:,} | {sum(e[c+'_invalid'] for c in COVERAGE):,} | {e['invalid_chronic_flag_cells']:,} |")
    lines += ['', '## Key-column missingness', '',
        'Empty strings after trimming are missing. Literal NA and other codes remain values.',
        'The JSON records every column; this table focuses on linking and interpretation keys.', '',
        '| File | Column | Missing rows | Missing percent |', '| --- | --- | ---: | ---: |']
    for kind,info in files.items():
        for col in ['DESYNPUF_ID','CLM_ID','PDE_ID','SEGMENT','PRVDR_NUM','AT_PHYSN_NPI',
                    'CLM_ADMSN_DT','NCH_BENE_DSCHRG_DT','BENE_DEATH_DT','PROD_SRVC_ID']:
            if col in info['null_counts']:
                lines.append(f"| {kind} | {col} | {info['null_counts'][col]:,} | {info['null_rates'][col]*100:.4f}% |")
    lines += ['', '## Reproduce and validate', '', 'Run `make profile` after `make download`.',
        'Input hashes are checked against the acquisition manifest. Expected row counts',
        'come from CMS Data Users Guide Table 2, PDF page 8 (printed page 5).',
        'SQLite temporary storage is discarded when the run completes. No database load',
        'or source-data filtering occurs. Step 3 must reconcile bronze against these exact counts.', '',
        '## Bronze reconciliation', '',
        'Step 3 database counts and financial checks are recorded separately in',
        '[bronze reconciliation](bronze_reconciliation.md), preserving this source baseline.', '']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chunksize',type=int,default=50000)
    args=parser.parse_args()
    if args.chunksize <= 0:parser.error('chunksize must be positive')
    started=time.monotonic()
    config=yaml.safe_load((ROOT/'ingest/urls.yaml').read_text())['samples'][1]
    paths={kind:ROOT/'data/extracted/sample_1'/spec['filename'].replace('.zip','.csv') for kind,spec in config.items()}
    manifest=read_manifest(ROOT/'data/manifest.csv')
    ccs_path=ROOT/'data/reference/ccs_2015/$dxref 2015.csv'
    for path in [*paths.values(),ccs_path]:
        verify_record(path,manifest[path.relative_to(ROOT).as_posix()])
    known,deaths,conflicts=beneficiary_context([path for kind,path in paths.items() if kind.startswith('beneficiary')])
    report=dict(sample=1, chunksize=args.chunksize, profiled_at_utc=datetime.now(timezone.utc).isoformat(),
        input_sha256={path.relative_to(ROOT).as_posix():manifest[path.relative_to(ROOT).as_posix()]['sha256'] for path in [*paths.values(),ccs_path]},
        conflicting_death_dates=conflicts, files={}, segments={})
    with tempfile.TemporaryDirectory(prefix='medicare-profile-') as directory:
        conn=sqlite3.connect(Path(directory)/'keys.sqlite')
        try:
            init_db(conn)
            ccs_codes=load_ccs(ccs_path)
            for kind,path in paths.items():
                print('Profiling',kind,flush=True)
                info=profile_file(path,kind,conn,known,deaths,ccs_codes,args.chunksize)
                info['cms_expected_rows']=EXPECTED_SAMPLE_1[kind]
                info['cms_row_count_matches']=info['rows']==EXPECTED_SAMPLE_1[kind]
                report['files'][kind]=info
                if kind in ('inpatient','outpatient'):
                    report['segments'][kind]=facility_stats(conn,kind)
                print(f"DONE {kind}: {info['rows']:,} rows",flush=True)
            report['carrier_overlapping_ids']=conn.execute('''SELECT COUNT(*) FROM ids a JOIN ids b
                ON a.value=b.value WHERE a.scope='carrier_a' AND b.scope='carrier_b' ''').fetchone()[0]
        finally:
            conn.close()
    report['elapsed_seconds']=round(time.monotonic()-started,2)
    (ROOT/'docs/data_profile.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    (ROOT/'docs/data_profile.md').write_text(render_report(report))
    if not all(info['cms_row_count_matches'] for info in report['files'].values()):
        raise SystemExit('FAIL: at least one source row count differs from CMS Table 2; see report')
    print(f"PASS: all eight row counts match CMS; profile complete in {report['elapsed_seconds']}s")


if __name__=='__main__':
    main()
