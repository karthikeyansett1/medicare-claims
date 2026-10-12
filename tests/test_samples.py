import json
import pytest
from ingest.samples import evidence_path, load_profiles, parse_samples


def test_sample_selection_and_evidence_are_separate(tmp_path):
    (tmp_path / 'docs').mkdir()
    for sample in [1, 2]:
        evidence_path(tmp_path, 'data_profile', sample).write_text(json.dumps(
            {'sample': sample, 'files': {'carrier_a': {'rows': sample}}}))
    profiles = load_profiles(tmp_path, parse_samples('1,2'))
    assert sum(p['files']['carrier_a']['rows'] for p in profiles) == 3
    assert evidence_path(tmp_path, 'data_profile', 1).name == 'data_profile.json'
    with pytest.raises(ValueError):
        parse_samples('1,1')
    with pytest.raises(ValueError):
        parse_samples('20')


def test_missing_hcpcs_expectation_accumulates_all_selected_samples():
    from decimal import Decimal
    from ingest.samples import missing_hcpcs_paid
    profiles = [
        {'files': {'carrier_a': {'quirks': {'paid_cents_missing_hcpcs': 101}},
                   'carrier_b': {'quirks': {'paid_cents_missing_hcpcs': -1}}}},
        {'files': {'carrier_a': {'quirks': {'paid_cents_missing_hcpcs': 230}},
                   'carrier_b': {'quirks': {'paid_cents_missing_hcpcs': 45}}}},
    ]
    assert missing_hcpcs_paid(profiles[:1]) == Decimal('1.00')
    assert missing_hcpcs_paid(profiles) == Decimal('3.75')
