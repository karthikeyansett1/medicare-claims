import pytest
from assistant.guardrails import validate_sql, GuardrailError

BASE='SELECT y.year FROM gold.dim_member_year AS y'

@pytest.mark.parametrize('suffix,limit',[('',500),(' LIMIT 5',5),(' LIMIT 9999',500),(' LIMIT 0',0),(' LIMIT ALL',500)])
def test_limit_cap(suffix,limit):
    assert validate_sql(BASE+suffix).endswith(f'LIMIT {limit}')

@pytest.mark.parametrize('sql',[
    'SELECT y.year FROM gold.dim_member_year y WHERE 1 OPERATOR(public.===) 1',
    'DROP TABLE gold.dim_member_year', BASE+'; SELECT 1',
    'WITH x AS (DELETE FROM gold.dim_member_year RETURNING *) SELECT * FROM x',
    'SELECT * INTO temp evil FROM gold.dim_member_year',BASE+' FOR UPDATE',
    'SELECT pg_sleep(20) FROM gold.dim_member_year',
    'SELECT pg_catalog.pg_sleep(20) FROM gold.dim_member_year',
    "SELECT set_config('default_transaction_read_only','off',false) FROM gold.dim_member_year",
    "SELECT pg_read_file('/etc/passwd') FROM gold.dim_member_year",
    "SELECT lo_import('/tmp/evil') FROM gold.dim_member_year",
    'SELECT * FROM pg_catalog.pg_authid', 'SELECT * FROM bronze.beneficiary',
    'SELECT * FROM dim_member_year','SELECT * FROM other.gold.dim_member_year',
    'SELECT * FROM generate_series(1,100)',
    'SELECT * FROM gold.dim_member_year CROSS JOIN generate_series(1,100)',
    'WITH RECURSIVE x AS (SELECT * FROM gold.dim_member_year) SELECT * FROM x',
    'SELECT nonexistent FROM gold.dim_member_year',
    'SELECT x.year FROM gold.dim_member_year AS y',
    BASE+' LIMIT (SELECT 1000)',
    "SELECT 'pg_class'::regclass FROM gold.dim_member_year",
    "SELECT 'x'::public.customtype FROM gold.dim_member_year",
    'SELECT * FROM gold.dim_member_year NATURAL JOIN gold.fct_member_year_cost',
    'SELECT * FROM gold.dim_member_year, gold.fct_member_year_cost',
    'SELECT * FROM gold.dim_member_year TABLESAMPLE SYSTEM (1)',
    "SELECT dblink('secret','select 1') FROM gold.dim_member_year",
    "SELECT current_setting('password') FROM gold.dim_member_year",
    'WITH dim_member_year AS (SELECT * FROM pg_catalog.pg_class) SELECT * FROM dim_member_year',
    'SELECT y.year FROM gold.dim_member_year y UNION SELECT 1',
    'SELECT y.year FROM gold.dim_member_year y WHERE EXISTS (SELECT * FROM pg_catalog.pg_class)',
])
def test_reject_unsafe(sql):
    with pytest.raises(GuardrailError): validate_sql(sql)

@pytest.mark.parametrize('sql',[
    'WITH x AS (SELECT y.year, COUNT(*) AS n FROM gold.dim_member_year y GROUP BY y.year) SELECT x.year, x.n FROM x',
    'SELECT y.year, SUM(c.medical_paid_amt) AS cost FROM gold.dim_member_year y JOIN gold.fct_member_year_cost c ON y.member_year_key=c.member_year_key GROUP BY y.year',
    'SELECT d.year FROM (SELECT y.year FROM gold.dim_member_year y) AS d',
    'SELECT COUNT(*) FILTER (WHERE y.is_ffs_eligible) AS eligible FROM gold.dim_member_year y',
    'SELECT y.year::numeric FROM gold.dim_member_year y',
])
def test_valid_analytics(sql):
    assert validate_sql(sql).endswith('LIMIT 500')


def test_exponential_string_cte_rejected():
    ctes = ["x0 AS (SELECT 'aaaaaaaaaa' AS s FROM gold.dim_member_year LIMIT 1)"]
    ctes += [f"x{i} AS (SELECT s || s AS s FROM x{i-1})" for i in range(1,21)]
    with pytest.raises(GuardrailError):
        validate_sql('WITH '+', '.join(ctes)+' SELECT s FROM x20')
