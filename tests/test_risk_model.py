import numpy as np
from analysis.risk_model import FLAGS, FEATURES, features, fit, diagnostics


def test_unknown_flags_are_not_absent_and_age_boundaries():
    row = dict.fromkeys(FLAGS, False)
    row.update(age_at_year_start=65, sex_cd=None)
    a = features(row)
    row[FLAGS[0]] = None
    b = features(row)
    assert len(a) == len(FEATURES)
    assert a[2] == 1 and a[8] == 1
    assert b[10] == 1 and a[10] == 0 and b[9] == 0
    row['age_at_year_start'] = None
    assert features(row)[5] == 1


def test_weighted_fit_preserves_constant_without_intercept_penalty():
    x = np.array([[1.,0.],[1.,1.],[1.,0.]])
    coef = fit(x,np.array([7.,7.,7.]),np.array([1.,12.,6.]))
    assert np.allclose(np.exp(x@coef),7)


def test_diagnostics_weight_by_exposure():
    d = diagnostics(np.array([0.,12.]),np.array([0.,0.]),np.array([12.,1.]))
    assert d['weighted_mae_pmpm'] == 12/13
    assert d['observed_paid'] == 12
