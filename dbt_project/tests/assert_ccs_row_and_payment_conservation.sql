with diagnosis_counts as (
    select (select count(*) from {{ ref('silver_diagnoses') }}) as source_rows,
        (select count(*) from {{ ref('silver_diagnoses_grouped') }}) as grouped_rows
), payments as (
    select sum(inpatient_paid) as paid, sum(inpatient_stays) as stays
    from {{ ref('mart_cost_by_ccs') }}
), source_payments as (
    select sum(paid_amt) as paid, count(*) as stays
    from {{ ref('fct_inpatient_stays') }}
)
select 'row_or_payment_mismatch' as issue
from diagnosis_counts, payments, source_payments
where source_rows != grouped_rows or payments.paid is distinct from source_payments.paid
    or payments.stays != source_payments.stays
