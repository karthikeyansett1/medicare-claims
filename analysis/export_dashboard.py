"""Publish only aggregate/provider data as an atomic, hash-verified snapshot."""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from analysis.compare_methods import query, run
from ingest.db import get_conn
from dashboard.data import FORBIDDEN

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dashboard/data'


def export(destination=OUT):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute('set transaction isolation level repeatable read read only')
        providers = query(conn, 'select * from marts.mart_provider_performance order by _sample_id,year,method,attributed_npi')
        conditions = query(conn, 'select * from marts.mart_cost_by_ccs order by year nulls last,ccs_category')
        # Recompute comparison artifacts from this same consistent warehouse snapshot.
        comparison_result = run(conn, export_only=True)
    # run returns frames; avoid publishing any member-grain diagnostic artifacts.
    summaries, pairs, coverage = comparison_result[:3]
    numeric = ['panel_size','member_months','medical_paid_amt','rx_gross_cost_amt','ed_claim_count','admissions','expected_medical_paid_amt','index_stays','readmissions']
    overview = providers.groupby(['_sample_id','year','method'], as_index=False)[numeric].sum()
    frames = {'providers': providers.loc[providers.meets_min_panel].copy(), 'overview': overview, 'conditions': conditions,
              'comparison': summaries, 'pairs': pairs, 'coverage': coverage}
    manifest = {'built_at': datetime.now(timezone.utc).isoformat(),
                'samples': sorted(providers._sample_id.unique().tolist()),
                'years': sorted(providers.year.unique().tolist()),
                'conditions_scope': 'All loaded samples pooled; no attribution filter',
                'definitions_sha256': hashlib.sha256((ROOT/'assistant/measure_definitions.md').read_bytes()).hexdigest(),
                'files': {}}
    for frame in frames.values():
        if FORBIDDEN.intersection(frame.columns):
            raise ValueError('Patient or claim identifiers are forbidden in public extracts')
    for name, frame in frames.items():
        data = frame.to_csv(index=False, float_format='%.12g', lineterminator='\n').encode()
        digest = hashlib.sha256(data).hexdigest()
        filename = f'{name}-{digest[:16]}.csv'
        with tempfile.NamedTemporaryFile('wb', dir=destination, delete=False) as handle:
            handle.write(data)
            staged = handle.name
        os.replace(staged, destination/filename)
        manifest['files'][name] = {'file': filename, 'sha256': digest, 'rows': len(frame)}
    with tempfile.NamedTemporaryFile('w', dir=destination, delete=False) as handle:
        json.dump(manifest, handle, indent=2)
        temp = handle.name
    os.replace(temp, destination/'manifest.json')
    print(json.dumps({k: len(v) for k, v in frames.items()}))
    return manifest

if __name__ == '__main__':
    export()
