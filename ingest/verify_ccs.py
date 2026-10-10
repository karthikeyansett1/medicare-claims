"""Independently reconstruct canonical inpatient CCS totals using the original map."""
import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from ingest.clean_ccs import read_map, normalize
from ingest.db import ROOT, get_conn


def main():
    mapping = read_map(ROOT / 'data/reference/ccs_2015/$dxref 2015.csv')
    expected = defaultdict(lambda: {'members': set(), 'stays': 0, 'paid': Decimal(0), 'missing': 0})
    with get_conn() as conn:
        conn.execute('set transaction isolation level repeatable read, read only')
        seed = {c: (cat, label) for c, cat, label in conn.execute('select * from gold.dim_dx_ccs')}
        assert seed == mapping
        for year, member, code, paid in conn.execute('select extract(year from admit_dt)::integer, member_key, principal_dx_cd, paid_amt from gold.fct_inpatient_stays'):
            cat = mapping.get(normalize(code or ''), ('UNMAPPED',))[0]
            item = expected[year, cat]
            item['members'].add(member)
            item['stays'] += 1
            item['paid'] += paid or Decimal(0)
            item['missing'] += paid is None
        actual = {(year, cat): (members, stays, paid, missing) for year, cat, members, stays, paid, missing in conn.execute('select year, ccs_category, member_count, inpatient_stays, inpatient_paid, missing_payment_stays from marts.mart_cost_by_ccs')}
        wanted = {k: (len(v['members']), v['stays'], v['paid'] if v['missing'] < v['stays'] else None, v['missing']) for k, v in expected.items()}
        assert actual == wanted
        coverage = []
        for kind, rows, matched in conn.execute('select claim_type, count(*), count(*) filter(where is_ccs_mapped) from silver.silver_diagnoses_grouped group by 1 order by 1'):
            coverage.append(dict(claim_type=kind, rows=rows, matched=matched, percent_matched=round(100*matched/rows,6)))
        source_count = conn.execute('select count(*) from silver.silver_diagnoses').fetchone()[0]
        assert sum(x['rows'] for x in coverage) == source_count
        # Independent aggregate mapping from ungrouped codes, not the join output.
        expected_matches = defaultdict(int)
        for kind, code, n in conn.execute('select claim_type, icd9_dx_cd, count(*) from silver.silver_diagnoses group by 1,2'):
            if normalize(code) in mapping:
                expected_matches[kind] += n
        assert all(x['matched'] == expected_matches[x['claim_type']] for x in coverage)
        unmatched = []
        for code, n in conn.execute('select icd9_dx_cd, count(*) from silver.silver_diagnoses_grouped where not is_ccs_mapped group by 1 order by 2 desc,1 limit 20'):
            normalized = normalize(code)
            extensions = [c for c in mapping if c.startswith(normalized)]
            unmatched.append(dict(code=code, rows=n, normalized=normalized, source_map_contains_code=normalized in mapping, longer_reference_codes=len(extensions), examples=extensions[:5], reason='Absent from the 2015 diagnosis reference; longer reference codes share this prefix.' if extensions else 'Absent from the 2015 diagnosis reference, including after case/decimal/space normalization. Historical validity or synthetic origin is not established.'))
        principal = list(conn.execute('select ccs_category,max(ccs_label),sum(inpatient_paid),sum(inpatient_stays) from marts.mart_cost_by_ccs group by 1 order by 3 desc,1 limit 10'))
        any_position = list(conn.execute('''with stay_categories as (
            select distinct f.stay_id, f.paid_amt, coalesce(d.ccs_category,'UNMAPPED') as category,
              coalesce(d.ccs_label,'Unmapped or missing diagnosis') as label
            from gold.fct_inpatient_stays f left join silver.silver_diagnoses_grouped d
            on f._sample_id=d._sample_id and f.member_id=d.member_id and f.claim_id=d.claim_id and d.claim_type='inpatient'
            ) select category,max(label),sum(paid_amt),count(*) from stay_categories group by 1 order by 3 desc,1 limit 10'''))
    report = dict(verified_at_utc=datetime.now(timezone.utc).isoformat(), reference_codes=len(mapping), checks='Exact reference equality; independent per-year/category member counts, stays, Decimal payments and missingness; source diagnosis count and independently mapped coverage.', category_year_groups=len(actual), inpatient_stays=sum(v['stays'] for v in expected.values()), inpatient_paid=str(sum(v['paid'] for v in expected.values())), coverage=coverage, overall_percent_matched=100*sum(x['matched'] for x in coverage)/source_count, top_unmatched=unmatched, principal_top10=principal, any_position_top10=any_position, any_position_limitation='Distinct stay/category assignments across all source segments and positions. A stay may appear in several categories, so payments are nonadditive across categories. Not a unique total.')
    (ROOT/'docs/ccs_verification.json').write_text(json.dumps(report, indent=2, default=str)+'\n')
    lines = ['# CCS verification', '', f"Verified {len(mapping):,} reference codes and {len(actual):,} category/year aggregates independently.", f"Conserved {report['inpatient_stays']:,} stays and ${report['inpatient_paid']} inpatient paid.", '', '| Claim type | Diagnosis rows | Matched | Coverage |', '|---|---:|---:|---:|']
    lines += [f"| {x['claim_type']} | {x['rows']:,} | {x['matched']:,} | {x['percent_matched']:.4f}% |" for x in coverage]
    lines += ['', '## Top unmatched codes', '', 'Normalization does not invent missing digits or convert prefixes into diagnoses. Prefix matches are evidence of ambiguity, not proof that a code is invalid. No historical codebook validation has established the origin of these unmatched codes.', '', '| Code | Rows | Longer reference codes | Evidence |','|---|---:|---:|---|']
    lines += [f"| {x['code']} | {x['rows']:,} | {x['longer_reference_codes']} | {x['reason']} Examples: {', '.join(x['examples'])} |" for x in unmatched]
    (ROOT/'docs/ccs_verification.md').write_text('\n'.join(lines)+'\n')
    lines = ['# Principal versus any-position CCS sensitivity', '', report['any_position_limitation'], '', 'Both approaches use the same 2015 grouper. This changes diagnosis-position assignment, not the grouper version. Principal uses the canonical lowest-segment header; any-position includes every source segment. Negative adjustments are retained.', '']
    for title, rows in [('Principal (additive)', principal), ('Any position (nonadditive)', any_position)]:
        lines += [f'## {title}', '', '| Rank | CCS | Label | Paid | Stay assignments |','|---:|---|---|---:|---:|']
        lines += [f'| {rank} | {cat} | {label} | {paid:,.2f} | {stays:,} |' for rank,(cat,label,paid,stays) in enumerate(rows,1)]
        lines += ['']
    pset={r[0] for r in principal}; aset={r[0] for r in any_position}
    lines += [f"Top-ten overlap: {len(pset & aset)}/10. Entering with any position: {', '.join(sorted(aset-pset))}. Leaving: {', '.join(sorted(pset-aset))}."]
    (ROOT/'analysis/ccs_sensitivity.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('top_unmatched','principal_top10','any_position_top10')},indent=2))


if __name__ == '__main__':
    main()
