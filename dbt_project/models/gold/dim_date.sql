{{ gold_config([{'columns':['date'],'unique':true}]) }}
-- Cover the configured analysis window AND every observed fact date, including 2007.
with dates as (
 select min(service_dt) as first_dt,max(service_end_dt) as last_dt from {{ ref('fct_professional_lines') }}
 union all select min(least(service_dt,service_start_dt)),max(greatest(discharge_dt,service_end_dt)) from {{ ref('fct_inpatient_stays') }}
 union all select min(service_dt),max(service_end_dt) from {{ ref('fct_outpatient_claims') }}
 union all select min(fill_dt),max(fill_dt) from {{ ref('fct_rx_fills') }}
), bounds as (
 select least(date '2008-01-01',min(first_dt)) as first_dt,
 greatest(date '2010-12-31',max(last_dt)) as last_dt from dates
)
select d::date as date,extract(year from d)::integer as year,
 extract(month from d)::integer as month,extract(quarter from d)::integer as quarter,
 extract(day from d)::integer as day_of_month,extract(isodow from d)::integer as iso_weekday,
 d::date between date '2008-01-01' and date '2010-12-31' as is_analysis_window
from bounds cross join lateral generate_series(first_dt::timestamp,last_dt::timestamp,interval '1 day') d
