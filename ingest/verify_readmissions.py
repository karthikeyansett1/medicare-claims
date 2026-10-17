"""Independently reconstruct episode merging, next admissions and eligibility in Python."""
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from psycopg.rows import dict_row
from ingest.db import ROOT, get_conn


def reconstruct(claims, members, years):
    grouped = defaultdict(list)
    for c in claims:
        grouped[c['member_key']].append(c)
    result = {}
    for member, claims in grouped.items():
        valid, invalid = [], []
        for c in claims:
            (valid if c['admit_dt'] and c['discharge_dt'] and c['admit_dt'] <= c['discharge_dt'] else invalid).append(c)
        episodes = []
        for c in sorted(valid, key=lambda c: (c['admit_dt'], c['discharge_dt'], c['stay_id'])):
            if episodes and c['admit_dt'] <= episodes[-1]['discharge_dt']:
                e = episodes[-1]
                e['discharge_dt'] = max(e['discharge_dt'], c['discharge_dt'])
                e['claims'].append(c)
            else:
                episodes.append(dict(admit_dt=c['admit_dt'], discharge_dt=c['discharge_dt'], claims=[c], valid=True))
        for i,e in enumerate(episodes):
            e['next'] = episodes[i+1] if i+1 < len(episodes) else None
        episodes += [dict(admit_dt=c['admit_dt'], discharge_dt=c['discharge_dt'], claims=[c], valid=False, next=None) for c in invalid]
        death = members[member]['death_dt']
        for e in episodes:
            dt, nxt = e['discharge_dt'], e['next']
            yr = dt.year if dt else None
            followyear = (dt + timedelta(days=30)).year if dt else None
            ey, fy = years.get((member,yr),{}), years.get((member,followyear),{})
            conflict = any(c['has_header_conflict'] for c in e['claims'])
            nextconflict = nxt and any(c['has_header_conflict'] for c in nxt['claims'])
            flags = [not e['valid'], bool(invalid), bool(conflict or nextconflict), yr not in (2009,2010), bool(death and dt and death<=dt), not dt or dt+timedelta(days=30)>date(2010,12,31), bool(death and dt and dt<death<=dt+timedelta(days=30)), not ey.get('is_ffs_eligible'), not (ey.get('is_full_year_ffs') and fy.get('is_full_year_ffs'))]
            reasons = ['01_invalid_dates','02_unordered_member','03_header_conflict','04_outside_performance_year','05_death_on_or_before_discharge','06_incomplete_data_window','07_death_in_followup','08_index_ffs_proxy','09_followup_ffs_proxy']
            reason = next((r for r,f in zip(reasons,flags) if f),None)
            ids=sorted(c['stay_id'] for c in e['claims'])
            nextdt=nxt['admit_dt'] if nxt else None
            days=(nextdt-dt).days if nextdt and dt else None
            result[ids[0]]=dict(merged_stay_id=ids[0],member_key=member,admit_dt=e['admit_dt'],discharge_dt=dt,source_stay_ids=ids,source_claim_count=len(ids),paid_amt=sum((c['paid_amt'] for c in e['claims'] if c['paid_amt'] is not None),Decimal(0)) if any(c['paid_amt'] is not None for c in e['claims']) else None,exclusion_reason=reason,next_admit_dt=nextdt,days_to_next_admit=days,is_index_eligible=reason is None,is_readmit_30d=(days is not None and 1<=days<=30) if reason is None else None,year=yr)
    return result


def main():
    with get_conn() as conn:
        conn.row_factory=dict_row
        claims=conn.execute('select * from gold.fct_inpatient_stays').fetchall()
        members={r['member_key']:r for r in conn.execute('select member_key,death_dt from gold.dim_member')}
        years={(r['member_key'],r['year']):r for r in conn.execute('select member_key,year,is_ffs_eligible,is_full_year_ffs from gold.dim_member_year')}
        expected=reconstruct(claims,members,years)
        actual={r['merged_stay_id']:r for r in conn.execute('select * from gold.fct_readmissions')}
        assert actual.keys()==expected.keys(), 'Episode population mismatch'
        comparisons=0
        for key,e in expected.items():
            for field,value in e.items():
                assert actual[key][field]==value, f'Episode reconciliation failed: {field}'
                comparisons+=1
        flattened=[id for e in expected.values() for id in e['source_stay_ids']]
        assert Counter(flattened)==Counter(c['stay_id'] for c in claims), 'Lost or repeated source claims'
        attrs=conn.execute('select member_key,_sample_id,attributed_npi,year,method from gold.attribution_long').fetchall()
        panels=Counter(); mapped={}
        for a in attrs:
            key=(a['_sample_id'],a['attributed_npi'],a['year'],a['method'])
            mapped[(a['member_key'],a['year'],a['method'])]=key
            if a['attributed_npi']:panels[key]+=1
        counts=defaultdict(lambda:[0,0]); coverage=defaultdict(lambda:[0,0])
        for e in expected.values():
            if not e['is_index_eligible']:continue
            for method in ['A_visits','B_allowed']:
                key=mapped.get((e['member_key'],e['year'],method))
                assigned=bool(key and key[1])
                coverage[(method,assigned)][0]+=1
                coverage[(method,assigned)][1]+=int(e['is_readmit_30d'])
                if assigned:
                    counts[key][0]+=1; counts[key][1]+=int(e['is_readmit_30d'])
        rates=conn.execute('select * from gold.readmission_provider_rates').fetchall()
        assert len(rates)==len(panels)
        for r in rates:
            key=(r['_sample_id'],r['attributed_npi'],r['year'],r['method']); n,k=counts[key]
            assert (r['attributed_members'],r['index_stays'],r['readmissions'],r['meets_panel_threshold'])==(panels[key],n,k,panels[key]>=20)
            assert r['readmission_rate'] is None if n==0 else abs(r['readmission_rate']-Decimal(k)/Decimal(n))<Decimal('1e-15')
        exclusions=Counter(e['exclusion_reason'] or 'eligible' for e in expected.values())
        denominator=exclusions['eligible']; numerator=sum(e['is_readmit_30d'] is True for e in expected.values())
        report=dict(source_claims=len(claims),merged_episodes=len(expected),field_comparisons=comparisons,provider_rows_checked=len(rates),denominator=denominator,numerator=numerator,rate=numerator/denominator if denominator else None,exclusions=dict(sorted(exclusions.items())),coverage=[dict(method=m,attributed=a,indices=n,readmissions=k) for (m,a),(n,k) in sorted(coverage.items())])
        (ROOT/'docs/readmission_verification.json').write_text(json.dumps(report,indent=2)+'\n')
        remaining=len(expected); lines=['# Readmission verification','',f'Independent Python reconstruction checked {comparisons:,} fields across {len(expected):,} episodes and {len(rates):,} provider rows. Every one of {len(claims):,} source claims occurs exactly once.','',f'Overall: {numerator:,} / {denominator:,} = {numerator/denominator:.4%}.','','| First exclusion | Removed | Remaining |','| --- | ---: | ---: |',f'| All merged/audit episodes | 0 | {remaining:,} |']
        for reason,n in sorted(exclusions.items()):
            if reason=='eligible':continue
            remaining-=n; lines.append(f'| {reason} | {n:,} | {remaining:,} |')
        lines+=['','Invalid/conflicting claims remain in source and financial reconciliation. Rates are synthetic, unadjusted, and use an annual enrollment proxy. See the canonical specification.','','| Attribution | Assigned | Eligible indices | Readmissions |','| --- | --- | ---: | ---: |']
        for c in report['coverage']:lines.append(f"| {c['method']} | {c['attributed']} | {c['indices']:,} | {c['readmissions']:,} |")
        (ROOT/'docs/readmission_verification.md').write_text('\n'.join(lines)+'\n')
        bymember=defaultdict(list)
        for e in expected.values():bymember[e['member_key']].append(e)
        selected=sorted((m for m,es in bymember.items() if len(es)>=3 and any(e['is_readmit_30d'] for e in es)))[:3]
        lines=['# Three member timeline spot checks','','Agent-verified against independently reconstructed source intervals; these are not human or clinical validation. Full claim IDs are synthetic. Every timeline below includes all episodes for that member, including exclusions.']
        for m in selected:
            lines+=['',f'## Synthetic member {m}','','| Source claim IDs | Admit | Discharge | Next admission | Days | Exclusion | Readmit |','| --- | --- | --- | --- | ---: | --- | --- |']
            for e in sorted(bymember[m],key=lambda e:e['admit_dt'] or date.min):lines.append(f"| {', '.join(e['source_stay_ids'])} | {e['admit_dt']} | {e['discharge_dt']} | {e['next_admit_dt']} | {e['days_to_next_admit']} | {e['exclusion_reason'] or 'eligible'} | {e['is_readmit_30d']} |")
        assert len(selected)==3
        (ROOT/'analysis/readmission_spot_check.md').write_text('\n'.join(lines)+'\n')
        print(json.dumps(report,indent=2))

if __name__=='__main__':main()
