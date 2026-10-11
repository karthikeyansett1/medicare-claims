import numpy as np
import pandas as pd
import pytest
from analysis.compare_methods import compare, ranked


def frame(values, sizes=None):
    return pd.DataFrame({'attributed_npi':[f'{i:02}' for i in range(len(values))],
                         'panel_size':sizes or [20]*len(values),'metric':values})


def test_ntile_uneven_buckets_and_npi_tie_breaker():
    r=ranked(frame([0]*12),'metric',20)
    assert r['rank'].tolist()==list(range(1,13))
    assert r.decile.tolist()==[1,1,2,2,3,4,5,6,7,8,9,10]
    assert r.index.tolist()==[f'{i:02}' for i in range(12)]


def test_threshold_recomputes_before_common_cohort():
    a=frame(list(range(11)),[20]*10+[10])
    b=frame(list(range(11)),[10]+[20]*10)
    result,pair=compare(a,b,'metric','metric',20)
    assert result['common_providers']==9
    assert pair.loc[pair.attributed_npi.eq('01'),'rank_left'].item()==2
    assert pair.loc[pair.attributed_npi.eq('01'),'rank_right'].item()==1
    assert result['spearman']==pytest.approx(1)
    assert result['top_union']==1 and result['top_jaccard']==0
    lower,_=compare(a,b,'metric','metric',10)
    assert lower['common_providers']==11 and lower['top_jaccard']==1


def test_constant_input_correlation_unavailable_even_when_ntile_splits_ties():
    result,_=compare(frame([0]*20),frame([0]*20),'metric','metric',20)
    assert result['spearman'] is None
    assert result['correlation_status']=='constant_input'
    assert result['top_jaccard']==1


def test_empty_union_is_unavailable():
    a=frame(list(range(11)),[20]*10+[10])
    b=frame(list(range(11)),[20]*9+[10,20])
    result,_=compare(a,b,'metric','metric',20)
    assert result['top_union']==0 and result['top_jaccard'] is None
    assert result['jaccard_status']=='empty_union'


def test_nulls_infinity_and_small_cohorts():
    result,pair=compare(frame([1,None,3,np.inf]),frame([1,2,3,4]),'metric','metric',20)
    assert len(pair)==2 and result['spearman'] is None
    assert result['correlation_status']=='too_few_common_providers'
    assert result['jaccard_status']=='too_few_qualifying_providers'
    assert result['top_jaccard'] is None and result['movement_0'] is None
    empty,_=compare(frame([1]),frame([1]),'metric','metric',30)
    assert empty['common_providers']==0 and empty['top_jaccard'] is None


def test_inverse_correlation_and_movement_buckets():
    result,pair=compare(frame(list(range(10))),frame(list(reversed(range(10)))),'metric','metric',20)
    assert result['spearman']==pytest.approx(-1)
    assert result['top_jaccard']==0
    assert result['movement_1']==2 and result['movement_3']==8
    assert result['movement_0']==result['movement_2']==0


def test_spearman_uses_average_tied_scores_not_npi_ranks():
    a=frame([1,1,2,2,3,3,4,4,5,5])
    b=frame([1,2,1,2,3,4,3,4,5,5])
    result,_=compare(a,b,'metric','metric',20)
    assert result['spearman']==pytest.approx(.9)


def test_zero_or_null_index_denominator_is_excluded_even_with_zero_rate():
    f=frame([0,0,.5]).rename(columns={'metric':'readmission_rate'})
    f['index_stays']=[0,None,2]
    r=ranked(f,'readmission_rate',20)
    assert r.index.tolist()==['02'] and r.value.tolist()==[.5]
