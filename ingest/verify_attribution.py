"""Reconstruct attribution independently from individual professional fact rows."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from statistics import median

from ingest.db import ROOT, get_conn


def choose(lines):
    """Python set/Decimal reconstruction; NULL allowed amounts never become zero."""
    candidates = {}
    for line_id, npi, date, em, allowed in lines:
        if npi is None:
            continue
        c = candidates.setdefault(npi, {'days': set(), 'office': set(), 'allowed': [], 'missing': 0})
        c['days'].add(date)
        if em:
            c['office'].add(date)
        if allowed is None:
            c['missing'] += 1
        else:
            c['allowed'].append(allowed)
    a = [(n, c) for n, c in candidates.items() if c['office']]
    b = [(n, c) for n, c in candidates.items() if c['allowed']]
    wa = min(a, key=lambda x: (-len(x[1]['office']), -max(x[1]['office']).toordinal(), x[0]))[0] if a else None
    wb = min(b, key=lambda x: (-sum(x[1]['allowed'], Decimal(0)), -len(x[1]['days']), x[0]))[0] if b else None
    return wa, wb, candidates


def main():
    with get_conn() as conn:
        conn.execute('set transaction isolation level repeatable read, read only')
        eligible = dict(conn.execute('select member_year_key, year from gold.dim_member_year where is_ffs_eligible and year in (2009,2010)').fetchall())
        actual = {(k, m): n for k, m, n in conn.execute('select member_year_key, method, attributed_npi from gold.attribution_long')}
        expected = {(k, m): None for k in eligible for m in ('A_visits', 'B_allowed')}
        spots = []
        def finish(key, rows):
            a, b, candidates = choose(rows)
            expected[key, 'A_visits'] = a
            expected[key, 'B_allowed'] = b
            if len(spots) < 5 and len(candidates) > 1:
                spots.append({'member_year_key': key, 'A_visits': a, 'B_allowed': b,
                              'lines': rows, 'candidates': {n: {'service_days': len(c['days']), 'office_days': len(c['office']), 'last_office': max(c['office']) if c['office'] else None, 'known_allowed': sum(c['allowed']) if c['allowed'] else None, 'missing_allowed': c['missing']} for n, c in candidates.items()}})
        count = 0
        with conn.cursor(name='attribution_fact_stream') as cur:
            cur.itersize = 20000
            cur.execute('''select e.member_year_key, f.claim_line_id, f.rendering_npi,
                f.service_dt, f.is_office_em, f.allowed_amt
                from gold.dim_member_year e join gold.fct_professional_lines f
                on e.member_key=f.member_key and e.year=extract(year from f.service_dt)::integer
                where e.is_ffs_eligible and e.year in (2009,2010)
                order by e.member_year_key, f.claim_line_id''')
            previous, rows = None, []
            for key, *line in cur:
                if previous is not None and key != previous:
                    finish(previous, rows)
                    rows = []
                previous = key
                rows.append(line)
                count += 1
            if previous is not None:
                finish(previous, rows)
        mismatches = sum(actual.get(k) != v or k not in actual for k, v in expected.items()) + len(set(actual)-set(expected))
        summary = []
        for year in (2009,2010):
            for method in ('A_visits','B_allowed'):
                keys = [k for k, y in eligible.items() if y == year]
                panels = Counter((k.split(':')[0], expected[k, method]) for k in keys if expected[k, method] is not None)
                attributed = sum(panels.values())
                summary.append(dict(year=year, method=method, eligible=len(keys), attributed=attributed, unattributed=len(keys)-attributed, coverage=attributed/len(keys), providers=len(panels), median_panel=median(panels.values()) if panels else 0, providers_panel_ge20=sum(n>=20 for n in panels.values())))
        report = dict(generated_at=datetime.now(timezone.utc).isoformat(), eligible_member_years=len(eligible), checked_fact_lines=count, reconstructed_assignments=len(expected), mismatches=mismatches, summary=summary, spot_check_count=len(spots), spot_checks_verified_by='agent, independently reconstructed in Python; not human-verified')
        (ROOT/'docs/attribution_verification.json').write_text(json.dumps(report,indent=2)+'\n')
        out=['# Attribution verification','',f'Independently reconstructed {len(expected):,} assignments from {count:,} individual fact rows. Mismatches: **{mismatches}**.','', '| Year | Method | Eligible | Attributed | Unattributed | Coverage | Median panel | Panels ≥20 |','| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for s in summary:
            out.append(f"| {s['year']} | {s['method']} | {s['eligible']:,} | {s['attributed']:,} | {s['unattributed']:,} | {s['coverage']:.2%} | {s['median_panel']} | {s['providers_panel_ge20']:,} |")
        (ROOT/'docs/attribution_verification.md').write_text('\n'.join(out)+'\n')
        (ROOT/'analysis').mkdir(exist_ok=True)
        (ROOT/'analysis/attribution_spot_check.json').write_text(json.dumps(spots,default=str,indent=2)+'\n')
        text=['# Five reproducible attribution spot checks','', 'These are **agent-verified**, not human-verified. Reproduce with `make verify-attribution`. The first five sorted eligible member-year keys with multiple candidate NPIs are selected deterministically. All their qualifying fact rows (including missing NPI rows) appear in the companion JSON; IDs are synthetic.','']
        for s in spots:
            text += [f"## {s['member_year_key']}", f"A winner: `{s['A_visits']}`; B winner: `{s['B_allowed']}`.", '', '| NPI | Distinct office days | Last office day | Distinct service days | Known allowed | Missing allowed lines |','| --- | ---: | --- | ---: | ---: | ---: |']
            for n,c in sorted(s['candidates'].items()):
                text.append(f"| {n} | {c['office_days']} | {c['last_office']} | {c['service_days']} | {c['known_allowed']} | {c['missing_allowed']} |")
            text += ['', 'A sorts office-day count descending, latest office date descending, then NPI ascending. B sorts known allowed sum descending, distinct service-day count descending, then NPI ascending. Only candidates with at least one known allowed amount qualify for B.', '']
        (ROOT/'analysis/attribution_spot_check.md').write_text('\n'.join(text)+'\n')
        print(json.dumps(report,indent=2))
        if mismatches:
            raise SystemExit('Attribution reconciliation failed')

if __name__ == '__main__':
    main()
