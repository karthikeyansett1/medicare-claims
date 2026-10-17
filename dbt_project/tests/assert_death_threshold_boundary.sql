-- A small fixture tests the actual warning predicate at and beyond its boundary.
with examples(service_dt,death_dt,expected) as (
 values (date '2008-01-31',date '2008-01-01',false),
 (date '2008-02-01',date '2008-01-01',true),
 (date '2007-12-31',date '2008-01-01',false),
 (null::date,date '2008-01-01',null::boolean),
 (date '2008-02-01',null::date,null::boolean)
)
select * from examples where ({{ after_death_threshold('service_dt','death_dt') }}) is distinct from expected
