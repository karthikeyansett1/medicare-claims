"""Four-page provider dashboard. Launch with make dashboard; no API calls."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import altair as alt
import streamlit as st
import yaml
from dashboard.data import ROOT, load_data, scoped, aggregate

st.set_page_config(page_title='Atlas | Provider analytics', page_icon='◈', layout='wide')
st.markdown('''<style>.stApp{background:#f5f8fa;color:#102b3d}h1,h2,h3{color:#102b3d}
[data-testid="stSidebar"]{background:#e6eff2}[data-testid="stMetric"]{background:white;padding:18px;border:1px solid #dce6ea;border-radius:10px;border-top:3px solid #148b87}
[data-testid="stMetricLabel"]{color:#45616d} div[data-testid="stMetricValue"]{font-size:1.65rem}</style>''', unsafe_allow_html=True)
@st.cache_data
def data(manifest_version):
    return load_data()
frames, manifest = data((ROOT/'dashboard/data/manifest.json').read_text())
with st.sidebar:
    st.markdown('## ◈ ATLAS')
    st.caption('PROVIDER PERFORMANCE')
    page = st.radio('Explore', ['Overview','Provider scorecard','Method comparison','Conditions'])
    pooled = page == 'Conditions'
    sample = st.selectbox('Sample', manifest['samples'], disabled=pooled)
    year = st.selectbox('Performance year', manifest['years'])
    method = st.selectbox('Attribution method', ['A_visits','B_allowed'],
                          format_func=lambda x: {'A_visits':'A · Visit plurality','B_allowed':'B · Allowed cost'}[x],
                          disabled=pooled or page == 'Method comparison')
    st.divider()
    st.caption('CMS DE-SynPUF · Synthetic data\n\nHistorical analysis, 2009–2010. Provider IDs are synthetic. Rankings describe cost, not clinical quality.')
    st.caption('Assistant: run `make assistant` and open localhost:8501. Questions require explicit submission and configured API access.')
st.caption('MEDICARE CLAIMS  /  ATTRIBUTION & PERFORMANCE')
st.title(page)
st.caption(('Samples '+', '.join(map(str,manifest['samples']))+' pooled · No attribution method' if pooled else f'Sample {sample} · '+('Methods A and B' if page=='Method comparison' else method.replace('A_visits','A · Visit plurality').replace('B_allowed','B · Allowed cost'))) + f' · {year}')
p = scoped(frames['providers'],sample,year,method)

def fmt(value, kind='number'):
    if value is None or pd.isna(value): return '—'
    return f'${value:,.2f}' if kind=='money' else f'{value:.1%}' if kind=='percent' else f'{value:,.2f}' if kind=='decimal' else f'{value:,.0f}'

def metrics(values, kinds=None):
    for col,(label,value) in zip(st.columns(len(values)),values.items()):
        col.metric(label,fmt(value,(kinds or {}).get(label,'number')))

def definitions(table, columns):
    semantic = yaml.safe_load((ROOT/'assistant/semantic_layer.yaml').read_text())
    with st.expander('Measure definitions & interpretation'):
        for name in columns:
            st.markdown(f"**{name.replace('_',' ').capitalize()}** — {semantic['tables'][table]['columns'][name]['meaning']}")
        st.markdown('[Read canonical measure definitions](https://github.com/karthikeyansett1/medicare-claims/blob/codex/step-14-dashboard/assistant/measure_definitions.md). Download a copy below for audit and reuse.')
        st.download_button('Download canonical definitions', (ROOT/'assistant/measure_definitions.md').read_text(), 'measure_definitions.md')

if page == 'Overview':
    p = scoped(frames['overview'],sample,year,method)
    st.markdown('### The attributed population at a glance')
    st.write('All attributed eligible members are included here, including panels below the 20-member ranking threshold.')
    metrics(aggregate(p), {'Medical PMPM':'money','Admissions / 1,000':'decimal','ED claims / 1,000':'decimal','30-day readmissions':'percent'})
    coverage=scoped(frames['coverage'],sample,year)
    if not coverage.empty:
        c=coverage.iloc[0]; a='a' if method=='A_visits' else 'b'
        st.info(f"{int(c['attributed_'+a]):,} of {int(c.eligible_members):,} eligible members attributed ({c['coverage_'+a]:.1%}). Unattributed members are outside these cost and utilization tiles.")
    left,right=st.columns([1.4,1])
    with left:
        st.subheader('Medical spending across methods')
        rows=[]
        for m,label in [('A_visits','A · Visit plurality'),('B_allowed','B · Allowed cost')]:
            f=scoped(frames['overview'],sample,year,m)
            rows.append({'Method':label,'Medical PMPM':aggregate(f)['Medical PMPM']})
        st.altair_chart(alt.Chart(pd.DataFrame(rows)).mark_bar(color='#148b87',cornerRadiusEnd=5).encode(x=alt.X('Medical PMPM:Q',axis=alt.Axis(format='$,.0f')),y='Method:N',tooltip=['Method','Medical PMPM']).properties(height=230),use_container_width=True)
    with right:
        st.subheader('Exposure & event counts')
        st.write(f"**{p.member_months.sum():,.0f}** proxy member-months")
        st.write(f"**{p.index_stays.sum():,.0f}** eligible index stays · **{p.readmissions.sum():,.0f}** readmissions")
        st.write(f"**{fmt(p.rx_gross_cost_amt.sum(),'money')}** Rx gross cost, reported separately from medical payments")
    definitions('marts.mart_provider_performance',['member_months','medical_pmpm','admissions_per_1000','ed_claims_per_1000','readmission_rate'])
elif page == 'Provider scorecard':
    st.write('Compare qualifying panels within one sample, year and attribution method. Decile 1 has the lowest cost; decile 10 the highest.')
    minimum=st.number_input('Minimum panel size',min_value=20,max_value=10000,value=20,step=10)
    search=st.text_input('Find synthetic NPI',placeholder='Enter all or part of an ID')
    f=p.loc[p.panel_size.ge(minimum) & p.meets_min_panel & p.attributed_npi.str.contains(search,regex=False,na=False)].copy()
    st.caption('Published ranks and deciles use the full ≥20-member reference population; increasing this display filter does not rerank providers.')
    if f.empty: st.info('No providers match these filters. Lower the panel filter or clear the NPI search.')
    else:
        npi=st.selectbox('Provider detail', sorted(f.attributed_npi.tolist()))
        r=f.loc[f.attributed_npi.eq(npi)].iloc[0]
        metrics({'Panel members':r.panel_size,'Medical PMPM':r.medical_pmpm,'Observed / expected':r.oe_ratio,'Cost decile':r.raw_decile}, {'Medical PMPM':'money','Observed / expected':'decimal'})
        st.caption(f"{r.member_months:,.0f} member-months · Medical paid USD {r.medical_paid_amt:,.2f} · Expected USD {r.expected_medical_paid_amt:,.2f} · Rx gross USD {r.rx_gross_cost_amt:,.2f}")
        st.warning(f"Readmissions: {fmt(r.readmissions)} / {fmt(r.index_stays)} eligible index stays ({fmt(r.readmission_rate,'percent')}). Small denominators can produce unstable rates; a 20-member panel does not establish reliability.")
        cols=['attributed_npi','panel_size','medical_pmpm','oe_ratio','admissions_per_1000','ed_claims_per_1000','index_stays','readmissions','readmission_rate','raw_decile','oe_decile']
        st.dataframe(f[cols].sort_values('medical_pmpm').style.background_gradient(subset=['raw_decile','oe_decile'],cmap='YlOrRd').format(precision=2,na_rep='—'),hide_index=True,use_container_width=True)
        st.download_button('Download filtered provider scorecard',f.to_csv(index=False),'provider_scorecard.csv')
    definitions('marts.mart_provider_performance',['panel_size','medical_pmpm','oe_ratio','raw_decile','readmission_rate'])
elif page == 'Method comparison':
    st.write('The attribution rule changes the panel—and the reference population used to rank it.')
    threshold=st.select_slider('Minimum panel for both comparison cohorts',options=[10,20,30],value=20)
    comparison=st.selectbox('Measure comparison',['A_vs_B_pmpm','A_vs_B_oe','A_vs_B_readmission','A_raw_vs_oe','B_raw_vs_oe'],format_func=lambda x: {'A_vs_B_pmpm':'A vs B · Medical PMPM','A_vs_B_oe':'A vs B · Observed / expected','A_vs_B_readmission':'A vs B · Readmission rate','A_raw_vs_oe':'Method A · Raw vs adjusted cost','B_raw_vs_oe':'Method B · Raw vs adjusted cost'}[x])
    def selected(name):
        f=scoped(frames[name],sample,year)
        return f.loc[f.min_panel.eq(threshold)&f.comparison.eq(comparison)]
    summary=selected('comparison'); pairs=selected('pairs')
    if summary.empty or pairs.empty: st.info('No shared providers for this selection.')
    else:
        r=summary.iloc[0]
        metrics({'Common providers':r.common_providers,'Spearman correlation':r.spearman,'High-decile overlap':r.top_jaccard}, {'Spearman correlation':'decimal','High-decile overlap':'percent'})
        st.caption(f"Reference populations: left {int(r.left_providers):,}; right {int(r.right_providers):,}. Ranks and deciles are assigned before intersecting cohorts. Spearman uses common-cohort scores with average ranks for ties.")
        left,right=st.columns([1.5,1])
        with left:
            st.altair_chart(alt.Chart(pairs).mark_circle(size=65,color='#148b87',opacity=.75).encode(x=alt.X('rank_left:Q',title='Left reference population rank',scale=alt.Scale(domain=[0,max(1,int(r.left_providers))])),y=alt.Y('rank_right:Q',title='Right reference population rank',scale=alt.Scale(domain=[0,max(1,int(r.right_providers))])),tooltip=['attributed_npi','rank_left','rank_right','decile_left','decile_right']).properties(height=330),use_container_width=True)
        with right:
            movement=pd.DataFrame({'Decile movement':['0','1','2','3+'],'Providers':[r[f'movement_{i}'] for i in range(4)]})
            st.altair_chart(alt.Chart(movement).mark_bar(color='#102b3d').encode(x='Decile movement:N',y='Providers:Q',tooltip=['Decile movement','Providers']).properties(height=330),use_container_width=True)
        st.caption('High-decile overlap is intersection ÷ union of decile-10 sets restricted to common providers. Threshold changes are sensitivity analyses, not confidence intervals. Readmission comparison requires a positive index-stay denominator.')
    definitions('marts.mart_provider_performance',['raw_rank','raw_decile','oe_ratio','index_stays'])
else:
    st.info('Conditions pool all loaded samples ('+', '.join(map(str, manifest['samples']))+'). Sample and attribution controls are disabled because this mart has neither dimension.')
    f=frames['conditions'].loc[frames['conditions'].year.eq(year)].copy()
    st.write('Principal-diagnosis CCS categories · Inpatient payments only')
    if f.empty: st.info('No inpatient categories for this year.')
    else:
        metrics({'Inpatient paid':f.inpatient_paid.sum(),'Claim-based stays':f.inpatient_stays.sum(),'Missing-payment stays':f.missing_payment_stays.sum()},{'Inpatient paid':'money'})
        top=f.nlargest(15,'inpatient_paid')
        st.altair_chart(alt.Chart(top).mark_bar(color='#148b87').encode(x=alt.X('inpatient_paid:Q',title='Inpatient paid',axis=alt.Axis(format='$,.2s',tickCount=5)),y=alt.Y('ccs_label:N',sort='-x',title=None,axis=alt.Axis(labelLimit=420)),tooltip=['ccs_label','inpatient_paid','member_count','inpatient_stays']).properties(height=430),use_container_width=True)
        st.caption('Top 15 categories by known inpatient payment. Each claim-based stay is assigned once. Category member counts overlap and must not be added; these are not total medical costs.')
        st.dataframe(top[['ccs_category','ccs_label','member_count','inpatient_stays','inpatient_paid']],hide_index=True,use_container_width=True)
    definitions('marts.mart_cost_by_ccs',['member_count','inpatient_stays','inpatient_paid','missing_payment_stays'])
st.divider()
st.caption(f"Snapshot built {manifest['built_at']} · Offline, aggregate/provider extracts · Annual eligibility and exposure use documented count proxies")
