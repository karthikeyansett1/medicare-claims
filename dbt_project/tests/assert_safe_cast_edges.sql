{{ config(tags=['step4']) }}
with dates(raw, expected) as (values
 ('20000229', date '2000-02-29'), ('19000229', null::date),
 ('20090230', null::date), ('20101301', null::date), ('00000101',null::date),
 ('99991231',date '9999-12-31'), ('20090100',null::date), ('x',null::date),
 (' 20080101 ',date '2008-01-01'), ('',null::date), (null,null::date)
), numbers(raw,expected) as (values
 (' -12.34 ', -12.34::numeric), ('001.20',1.20::numeric),
 ('1.234',1.234::numeric), ('NaN',null::numeric), ('Infinity',null::numeric),
 ('1e4',null::numeric), ('',null::numeric), ('1,200',null::numeric),
 ('999999999999999999999999999999999',null::numeric)
)
select 'date' as failed_type, raw from dates where ({{ safe_date('raw') }}) is distinct from expected
union all
select 'numeric',raw from numbers where ({{ safe_numeric('raw') }}) is distinct from expected
union all
select 'integer',raw from (values ('-1'),('1.5'),('2147483648'),('abc')) i(raw)
where ({{ safe_integer('raw') }}) is not null
union all
select 'flag',raw from (values ('0'),('3'),('Y'),('')) f(raw)
where ({{ safe_flag('raw') }}) is not null
union all
select 'flag_mapping',raw from (values ('1',true),('2',false)) f(raw,expected)
where ({{ safe_flag('raw') }}) is distinct from expected
union all
select 'integer_valid',raw from (values ('0001',1),('0',0),('999999999',999999999)) i(raw,expected)
where ({{ safe_integer('raw') }}) is distinct from expected
