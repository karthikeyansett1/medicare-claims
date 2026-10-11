"""Deterministic descriptive positive-mean GLM; JSON artifacts, no executable serialization."""
import json
import hashlib
import numpy as np
import warnings
from sklearn.linear_model import PoissonRegressor
from sklearn.exceptions import ConvergenceWarning
from psycopg.rows import dict_row
from ingest.db import get_conn, ROOT

FLAGS = "sp_alzhdmta sp_chf sp_chrnkidn sp_cncr sp_copd sp_depressn sp_diabetes sp_ischmcht sp_osteoprs sp_ra_oa sp_strketia".split()
FEATURES = ["intercept"] + ["age_" + x for x in ["under65", "65to74", "75to84", "85plus", "unknown"]] + ["sex_" + x for x in ["1", "2", "unknown"]] + [f + s for f in FLAGS for s in ["_present", "_unknown"]]
ALPHA = 1.0


def features(row):
    age = row["age_at_year_start"]
    band = 4 if age is None or age < 0 else (0 if age < 65 else 1 if age < 75 else 2 if age < 85 else 3)
    sex = {"1": 0, "2": 1}.get(row["sex_cd"], 2)
    return [1.0] + [float(band == i) for i in range(5)] + [float(sex == i) for i in range(3)] + [v for f in FLAGS for v in (float(row[f] is True), float(row[f] is None))]

def fit(x, y, weights):
    model = PoissonRegressor(alpha=ALPHA, max_iter=1000, tol=1e-8)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(x[:, 1:], y, sample_weight=weights)
    return np.r_[model.intercept_, model.coef_]


def diagnostics(actual, predicted, weights):
    return {"member_years": len(actual), "exposure_months": int(weights.sum()),
            "weighted_mae_pmpm": float(np.average(np.abs(actual-predicted), weights=weights)),
            "weighted_rmse_pmpm": float(np.sqrt(np.average((actual-predicted)**2, weights=weights))),
            "observed_paid": float(np.sum(actual * weights)), "expected_paid": float(np.sum(predicted * weights))}

def main():
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""select y.*, c.medical_paid_amt from gold.dim_member_year y
                join gold.fct_member_year_cost c using(member_year_key)
                where y.is_ffs_eligible and y.required_months > 0 and y.year between 2008 and 2010
                order by y.member_year_key""")
            rows = cur.fetchall()
        x = np.asarray([features(r) for r in rows])
        w = np.asarray([r["required_months"] for r in rows], dtype=float)
        y = np.asarray([float(r["medical_paid_amt"]) for r in rows]) / w
        years = np.asarray([r["year"] for r in rows])
        train = (years == 2008) & (y >= 0)
        if train.sum() < x.shape[1]:
            raise ValueError("Insufficient 2008 training rows")
        coef = fit(x[train], y[train], w[train])
        pred = np.exp(x @ coef)
        if not np.all(np.isfinite(pred)) or np.any(pred <= 0):
            raise ValueError("Nonpositive/nonfinite expected costs; do not publish O/E until reviewed")
        baseline = np.average(y[years == 2008], weights=w[years == 2008])
        artifact = {"training_year": 2008, "application_years": [2009, 2010], "alpha": ALPHA,
                    "model": "exposure-weighted Poisson quasi-likelihood GLM with log link; L2 regularization; unpenalized intercept",
                    "excluded_negative_training_rows": int(((years == 2008) & (y < 0)).sum()),
                    "features": dict(zip(FEATURES, map(float, coef))), "baseline_pmpm": float(baseline),
                    "limitations": "Fixed alpha=1 before GLM temporal evaluation. Earlier linear and log-smearing attempts were inspected; this is development temporal evaluation, not untouched validation. Costs are continuous, not assumed Poisson-distributed. Concurrent annual chronic flags; descriptive adjustment, not a clinical or prospective forecast. Temporal evaluation can include the same members.",
                    "by_year": {str(yr): {"model": diagnostics(y[years==yr], pred[years==yr], w[years==yr]),
                                         "mean_baseline": diagnostics(y[years==yr], np.full((years==yr).sum(), baseline), w[years==yr]),
                                         "negative_observed_member_years": int(((years==yr) & (y < 0)).sum()),
                                         "minimum_expected_pmpm": float(pred[years==yr].min())} for yr in [2008,2009,2010]}}
        model_id = hashlib.sha256(json.dumps(artifact, sort_keys=True).encode()).hexdigest()
        artifact["model_id"] = model_id
        conn.execute("create schema if not exists analysis")
        # One transaction: existing readers never see a partial refresh; preserve table identity.
        conn.execute("""create table if not exists analysis.expected_cost (
            member_year_key text primary key, expected_medical_paid_amt double precision not null,
            expected_medical_pmpm double precision not null, required_months integer not null,
            model_id text not null)""")
        conn.execute("delete from analysis.expected_cost")
        with conn.cursor().copy("copy analysis.expected_cost from stdin") as copy:
            for i,r in enumerate(rows):
                if r["year"] in (2009,2010):
                    copy.write_row((r["member_year_key"], float(pred[i]*w[i]), float(pred[i]), int(w[i]), model_id))
    output = ROOT / "analysis/risk_model_diagnostics.json"
    output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({"model_id": model_id, "application_rows": int((years!=2008).sum()), "diagnostics": artifact["by_year"]}, indent=2))

if __name__ == "__main__":
    main()
