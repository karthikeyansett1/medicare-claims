"""Create a deterministic text-only seed from the public AHRQ 2015 CCS map."""
import csv
import re
from ingest.db import ROOT


def clean(value):
    return value.strip().strip("'\"").strip()


def normalize(value):
    return clean(value).upper().replace('.', '')


def read_map(path):
    result = {}
    with path.open(newline='', encoding='utf-8-sig') as handle:
        rows = csv.reader(handle)
        for row in rows:
            if row and clean(row[0]) == 'ICD-9-CM CODE':
                break
        else:
            raise ValueError('CCS header missing')
        for row in rows:
            if not row:
                continue
            if len(row) < 3:
                raise ValueError('Truncated CCS row')
            code = normalize(row[0])
            if not code:
                continue  # AHRQ blank-code No DX placeholder is not a diagnosis.
            category, label = clean(row[1]), clean(row[2])
            if not re.fullmatch(r'[A-Z0-9]+', code) or not category.isdigit() or not label:
                raise ValueError('Invalid CCS mapping')
            value = (category, label)
            if code in result and result[code] != value:
                raise ValueError(f'Conflicting CCS mapping: {code}')
            result[code] = value
    return result


def main():
    mapping = read_map(ROOT / 'data/reference/ccs_2015/$dxref 2015.csv')
    target = ROOT / 'dbt_project/seeds/ccs_dx_map.csv'
    with target.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['icd9_dx_cd', 'ccs_category', 'ccs_label'])
        writer.writerows((code, *mapping[code]) for code in sorted(mapping))
    print(f'Wrote {len(mapping):,} unique diagnosis mappings to {target}')


if __name__ == '__main__':
    main()
