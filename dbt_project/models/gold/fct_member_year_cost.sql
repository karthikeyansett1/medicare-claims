{{ gold_config([{'columns':['cost_year_key'],'unique':true}, {'columns':['member_key','year']}, {'columns':['member_id','year']}]) }}
with by_source as (
select _sample_id,member_id,extract(year from service_dt)::integer as year,
sum(paid_amt)::numeric as inpatient_paid_amt,
0::numeric as outpatient_paid_amt,
0::numeric as professional_paid_amt,
0::numeric as professional_allowed_amt,
0::numeric as rx_gross_cost_amt,
0::numeric as rx_patient_pay_amt,
count(*)::bigint as inpatient_claim_episode_count,
0::bigint as outpatient_claim_count,
0::bigint as ed_claim_count,
0::bigint as professional_line_count,
0::bigint as office_em_line_count,
0::bigint as rx_fill_count,
sum(missing_payment_segments)::bigint as missing_medical_payment_count,
0::bigint as missing_rx_gross_cost_count
from {{ ref('fct_inpatient_stays') }} group by _sample_id,member_id,extract(year from service_dt)::integer
union all
select _sample_id,member_id,extract(year from service_dt)::integer as year,
0::numeric as inpatient_paid_amt,
sum(paid_amt)::numeric as outpatient_paid_amt,
0::numeric as professional_paid_amt,
0::numeric as professional_allowed_amt,
0::numeric as rx_gross_cost_amt,
0::numeric as rx_patient_pay_amt,
0::bigint as inpatient_claim_episode_count,
count(*)::bigint as outpatient_claim_count,
count(*) filter(where is_ed_visit)::bigint as ed_claim_count,
0::bigint as professional_line_count,
0::bigint as office_em_line_count,
0::bigint as rx_fill_count,
sum(missing_payment_segments)::bigint as missing_medical_payment_count,
0::bigint as missing_rx_gross_cost_count
from {{ ref('fct_outpatient_claims') }} group by _sample_id,member_id,extract(year from service_dt)::integer
union all
select _sample_id,member_id,extract(year from service_dt)::integer as year,
0::numeric as inpatient_paid_amt,
0::numeric as outpatient_paid_amt,
sum(paid_amt)::numeric as professional_paid_amt,
sum(allowed_amt)::numeric as professional_allowed_amt,
0::numeric as rx_gross_cost_amt,
0::numeric as rx_patient_pay_amt,
0::bigint as inpatient_claim_episode_count,
0::bigint as outpatient_claim_count,
0::bigint as ed_claim_count,
count(*)::bigint as professional_line_count,
count(*) filter(where is_office_em)::bigint as office_em_line_count,
0::bigint as rx_fill_count,
count(*) filter(where paid_amt is null)::bigint as missing_medical_payment_count,
0::bigint as missing_rx_gross_cost_count
from {{ ref('fct_professional_lines') }} group by _sample_id,member_id,extract(year from service_dt)::integer
union all
select _sample_id,member_id,extract(year from fill_dt)::integer as year,
0::numeric as inpatient_paid_amt,
0::numeric as outpatient_paid_amt,
0::numeric as professional_paid_amt,
0::numeric as professional_allowed_amt,
sum(gross_drug_cost_amt)::numeric as rx_gross_cost_amt,
sum(patient_pay_amt)::numeric as rx_patient_pay_amt,
0::bigint as inpatient_claim_episode_count,
0::bigint as outpatient_claim_count,
0::bigint as ed_claim_count,
0::bigint as professional_line_count,
0::bigint as office_em_line_count,
count(*)::bigint as rx_fill_count,
0::bigint as missing_medical_payment_count,
count(*) filter(where gross_drug_cost_amt is null)::bigint as missing_rx_gross_cost_count
from {{ ref('fct_rx_fills') }} group by _sample_id,member_id,extract(year from fill_dt)::integer
union all
select _sample_id,member_id,year,0::numeric as inpatient_paid_amt,0::numeric as outpatient_paid_amt,0::numeric as professional_paid_amt,0::numeric as professional_allowed_amt,0::numeric as rx_gross_cost_amt,0::numeric as rx_patient_pay_amt,0::bigint as inpatient_claim_episode_count,0::bigint as outpatient_claim_count,0::bigint as ed_claim_count,0::bigint as professional_line_count,0::bigint as office_em_line_count,0::bigint as rx_fill_count,0::bigint as missing_medical_payment_count,0::bigint as missing_rx_gross_cost_count from {{ ref('dim_member_year') }}
), combined as (
 select _sample_id,member_id,year,
coalesce(sum(inpatient_paid_amt),0)::numeric as inpatient_paid_amt,
coalesce(sum(outpatient_paid_amt),0)::numeric as outpatient_paid_amt,
coalesce(sum(professional_paid_amt),0)::numeric as professional_paid_amt,
coalesce(sum(professional_allowed_amt),0)::numeric as professional_allowed_amt,
coalesce(sum(rx_gross_cost_amt),0)::numeric as rx_gross_cost_amt,
coalesce(sum(rx_patient_pay_amt),0)::numeric as rx_patient_pay_amt,
coalesce(sum(inpatient_claim_episode_count),0)::bigint as inpatient_claim_episode_count,
coalesce(sum(outpatient_claim_count),0)::bigint as outpatient_claim_count,
coalesce(sum(ed_claim_count),0)::bigint as ed_claim_count,
coalesce(sum(professional_line_count),0)::bigint as professional_line_count,
coalesce(sum(office_em_line_count),0)::bigint as office_em_line_count,
coalesce(sum(rx_fill_count),0)::bigint as rx_fill_count,
coalesce(sum(missing_medical_payment_count),0)::bigint as missing_medical_payment_count,
coalesce(sum(missing_rx_gross_cost_count),0)::bigint as missing_rx_gross_cost_count
 from by_source group by _sample_id,member_id,year
)
select {{ member_key('c._sample_id','c.member_id') }} || ':' || coalesce(c.year::text,'unknown') as cost_year_key,
 {{ member_key('c._sample_id','c.member_id') }} as member_key,y.member_year_key,
 c.*,(y.member_year_key is not null) as has_annual_enrollment,
 coalesce(c.year between 2008 and 2010,false) as is_analysis_window,
 c.inpatient_paid_amt+c.outpatient_paid_amt+c.professional_paid_amt as medical_paid_amt
from combined c left join {{ ref('dim_member_year') }} y
 on c._sample_id=y._sample_id and c.member_id=y.member_id and c.year=y.year
