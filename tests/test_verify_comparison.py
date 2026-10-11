"""Exercise independent verifier SQL using isolated temporary PostgreSQL fixtures."""
import os
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from analysis.compare_methods import compare
from analysis.verify_comparison import live_comparison, assert_comparison, assert_mart_consistency
from ingest.db import get_conn


def providers(values,method):
    return pd.DataFrame({'attributed_npi':[f'{i:02}' for i in range(len(values))],
        'panel_size':20,'medical_pmpm':values,'oe_ratio':values,'method':method,
        '_sample_id':1,'year':2009,'index_stays':1})


@pytest.mark.skipif(os.getenv('RUN_DB_TESTS')!='1',reason='Set RUN_DB_TESTS=1 for PostgreSQL fixture checks')
@pytest.mark.parametrize('left,right',[
    ([1,2,float('nan'),float('inf'),float('-inf')],[2,1,3,4,5]),
    ([1,2,3],list(range(12))),
    ([1,1,1],[2,2,2]),
    ([float('nan'),float('inf')],[float('-inf'),None]),
    (list(range(12)),list(reversed(range(12)))),
    (list(range(10))+[float('nan')],list(range(9))+[float('nan'),10]),
])
def test_sql_verifier_handles_nonfinite_and_unavailable_results(left,right):
    a,b=providers(left,'A_visits'),providers(right,'B_allowed')
    result,pairs=compare(a,b,'medical_pmpm','medical_pmpm',20)
    with get_conn() as conn:
        conn.execute('''create temporary table comparison_fixture (
          _sample_id int,year int,attributed_npi text,panel_size int,method text,
          medical_pmpm double precision,index_stays int) on commit drop''')
        for frame in (a,b):
            with conn.cursor().copy('copy comparison_fixture from stdin') as copy:
                for row in frame.itertuples(index=False):
                    copy.write_row((1,2009,row.attributed_npi,20,row.method,row.medical_pmpm,1))
        live,counts=live_comparison(conn,1,2009,20,'A_vs_B_pmpm',('comparison_fixture',))
        assert_comparison(live,counts,pairs,SimpleNamespace(**result))
        # A bogus zero in place of unavailable must fail, as must a false status.
        broken=dict(result)
        broken['decile_status']='incorrect'
        with pytest.raises(AssertionError):
            assert_comparison(live,counts,pairs,SimpleNamespace(**broken))
        if result['spearman'] is None:
            broken=dict(result,spearman=0)
            with pytest.raises(AssertionError):
                assert_comparison(live,counts,pairs,SimpleNamespace(**broken))
        if result['movement_0'] is None:
            broken=dict(result,movement_0=0)
            with pytest.raises(AssertionError):
                assert_comparison(live,counts,pairs,SimpleNamespace(**broken))
        if result['top_jaccard'] is None:
            broken=dict(result,top_jaccard=0)
            with pytest.raises(AssertionError):
                assert_comparison(live,counts,pairs,SimpleNamespace(**broken))


def test_mart_verifier_respects_small_population_decile_availability():
    a,b=providers([1,2,3],'A_visits'),providers([1,2,3],'B_allowed')
    _,pairs=compare(a,b,'medical_pmpm','medical_pmpm',20)
    pairs=pairs.assign(_sample_id=1,year=2009,min_panel=20,comparison='A_vs_B_pmpm')
    mart=pd.concat([a,b],ignore_index=True)
    for prefix in ['raw','oe']:
        mart[f'{prefix}_rank']=[1,2,3]*2
        mart[f'{prefix}_decile']=[1,2,3]*2
    checks,skipped=assert_mart_consistency(pairs,mart)
    assert checks==12 and skipped==0
    broken=pairs.copy();broken['decile_left']=1
    with pytest.raises(AssertionError):
        assert_mart_consistency(broken,mart)
    # A nonfinite scored row remains ranked in the operational mart. It changes
    # its reference population, so direct rank equality is inapplicable.
    mart['medical_pmpm']=mart.medical_pmpm.astype(float)
    mart.loc[mart.method.eq('A_visits') & mart.attributed_npi.eq('02'),'medical_pmpm']=np.inf
    _,skipped=assert_mart_consistency(pairs,mart)
    assert skipped==1
