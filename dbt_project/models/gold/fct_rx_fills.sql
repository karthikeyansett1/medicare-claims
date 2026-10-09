{{ gold_config([{'columns':['fill_id'],'unique':true}, {'columns':['member_key']}, {'columns':['member_id']}]) }}
select fill_id,{{ member_key() }} as member_key,
 _sample_id,member_id,pde_id,service_dt as fill_dt,drug_code,
 quantity_dispensed,days_supply,gross_drug_cost_amt,patient_pay_amt,
 _source_file,_loaded_at
from {{ ref('silver_pde_fills') }}
