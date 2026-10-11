{{ config(materialized='table', tags=['step10'],
    indexes=[{'columns':['_sample_id','attributed_npi','year','method'],'unique':true}]) }}
with admissions as (
    select
        member_key,
        extract(year from admit_dt)::integer as year,
        count(*) as admissions
    from {{ ref('int_stays_merged') }}
    where valid_dates
    group by member_key, extract(year from admit_dt)::integer
),

panels as (
    select
        a._sample_id,
        a.attributed_npi,
        a.year,
        a.method,
        count(*) as panel_size,
        sum(y.required_months) as member_months,
        sum(c.medical_paid_amt) as medical_paid_amt,
        sum(c.rx_gross_cost_amt) as rx_gross_cost_amt,
        sum(c.ed_claim_count) as ed_claim_count,
        sum(coalesce(i.admissions, 0)) as admissions,
        sum(e.expected_medical_paid_amt)::numeric as expected_medical_paid_amt,
        count(*) filter (where e.member_year_key is null) as missing_expected_members
    from {{ ref('attribution_long') }} as a
    inner join {{ ref('dim_member_year') }} as y using (member_year_key)
    inner join {{ ref('fct_member_year_cost') }} as c using (member_year_key)
    left join admissions as i on a.member_key = i.member_key and a.year = i.year
    left join {{ source('analysis', 'expected_cost') }} as e using (member_year_key)
    where a.attributed_npi is not null
    group by a._sample_id, a.attributed_npi, a.year, a.method
),

metrics as (
    select
        p.*,
        p.panel_size >= 20 as meets_min_panel,
        p.medical_paid_amt / nullif(p.member_months, 0) as medical_pmpm,
        p.rx_gross_cost_amt / nullif(p.member_months, 0) as rx_gross_pmpm,
        p.admissions * 12000::numeric / nullif(p.member_months, 0) as admissions_per_1000,
        p.ed_claim_count * 12000::numeric / nullif(p.member_months, 0) as ed_claims_per_1000,
        case
            when p.missing_expected_members = 0 then
                p.medical_paid_amt / nullif(p.expected_medical_paid_amt, 0)
        end as oe_ratio,
        r.index_stays,
        r.readmissions,
        r.readmission_rate
    from panels as p
    left join {{ ref('readmission_provider_rates') }} as r
        using (_sample_id, attributed_npi, year, method)
),

ranked as (
    select
        _sample_id,
        attributed_npi,
        year,
        method,
        row_number() over (partition by _sample_id, year, method order by medical_pmpm, attributed_npi) as raw_rank,
        ntile(10) over (partition by _sample_id, year, method order by medical_pmpm, attributed_npi) as raw_decile,
        row_number() over (partition by _sample_id, year, method order by oe_ratio, attributed_npi) as oe_rank,
        ntile(10) over (partition by _sample_id, year, method order by oe_ratio, attributed_npi) as oe_decile
    from metrics
    where meets_min_panel and member_months > 0 and oe_ratio is not null
)

select
    m.*,
    r.raw_rank,
    r.raw_decile,
    r.oe_rank,
    r.oe_decile
from metrics as m left join ranked as r using (_sample_id, attributed_npi, year, method)
