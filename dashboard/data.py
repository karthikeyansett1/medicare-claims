"""Offline loading, privacy validation and weighted aggregate measures."""
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'member_id','member_key','member_year_key','claim_id','merged_stay_id','source_stay_ids'}


def load_data(directory=None):
    directory = Path(directory or ROOT/'dashboard/data')
    manifest = json.loads((directory/'manifest.json').read_text())
    frames = {}
    for name, spec in manifest['files'].items():
        path = directory/spec['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != spec['sha256']:
            raise ValueError(f'Extract checksum mismatch: {name}')
        frame = pd.read_csv(path, dtype={'attributed_npi':'string','ccs_category':'string'})
        if FORBIDDEN.intersection(frame.columns):
            raise ValueError('Patient or claim identifiers are not permitted in public extracts')
        frames[name] = frame
    return frames, manifest


def scoped(frame, sample, year, method=None):
    result = frame.loc[frame._sample_id.eq(sample) & frame.year.eq(year)]
    return result.loc[result.method.eq(method)] if method is not None else result


def aggregate(frame):
    def ratio(numerator, denominator, factor=1):
        denom = frame[denominator].sum()
        return frame[numerator].sum()/denom*factor if denom else None
    return {'Members': frame.panel_size.sum(), 'Medical PMPM': ratio('medical_paid_amt','member_months'),
            'Admissions / 1,000': ratio('admissions','member_months',12000),
            'ED claims / 1,000': ratio('ed_claim_count','member_months',12000),
            '30-day readmissions': ratio('readmissions','index_stays')}
