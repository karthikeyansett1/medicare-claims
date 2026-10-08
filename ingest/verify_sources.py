"""Verify acquisition completeness and beneficiary sample consistency offline."""
import csv
import json
from pathlib import Path

from ingest.download import ROOT


def verify(root=ROOT, sample=1):
    folder = root / f'data/extracted/sample_{sample}'
    files = sorted(folder.glob('*.csv'))
    if len(files) != 8:
        raise ValueError(f'Expected 8 CSVs, found {len(files)}')
    members = {}
    for year in (2008, 2009, 2010):
        path = folder / f'DE1_0_{year}_Beneficiary_Summary_File_Sample_{sample}.csv'
        with path.open(newline='') as stream:
            ids = [row['DESYNPUF_ID'] for row in csv.DictReader(stream)]
        if not ids or '' in ids or len(ids) != len(set(ids)):
            raise ValueError(f'Empty, missing or duplicated beneficiary IDs for {year}')
        members[year] = set(ids)
        if members[year] - members[2008]:
            raise ValueError(f'{year} contains beneficiaries outside the 2008 sample')
    ccs = root / 'data/reference/ccs_2015/$dxref 2015.csv'
    with ccs.open(newline='') as stream:
        reader = csv.reader(stream)
        next(reader)  # Source explanatory note.
        header = [v.strip(" '") for v in next(reader)]
        if header[:2] != ['ICD-9-CM CODE', 'CCS CATEGORY']:
            raise ValueError('Unexpected CCS diagnosis mapping header')
        codes = [row[0].strip(" '") for row in reader]
    valid_codes = [code for code in codes if code]
    if len(valid_codes) != len(set(valid_codes)):
        raise ValueError('Duplicate ICD-9 diagnosis codes in the source map')
    report = {
        'sample': sample, 'csv_files': len(files),
        'beneficiary_counts': {str(year): len(ids) for year, ids in members.items()},
        'later_year_ids_outside_2008': {str(year): len(ids-members[2008])
                                     for year, ids in members.items() if year != 2008},
        'ccs_nonblank_diagnosis_codes': len(valid_codes),
        'ccs_blank_code_rows': len(codes)-len(valid_codes),
        'scope': 'Acquisition checks only; full claims profiling and reconciliation are later steps.',
    }
    (root / 'docs/source_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    verify()
