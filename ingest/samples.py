"""Sample selection and evidence paths shared by ingestion and reconciliation."""
import json
from decimal import Decimal
import os
from pathlib import Path

DEFAULT_SAMPLES = "1,2"
EXPECTED_ROWS = {
    1: dict(beneficiary_2008=116352, beneficiary_2009=114538,
            beneficiary_2010=112754, inpatient=66773, outpatient=790790,
            carrier_a=2370667, carrier_b=2370668, pde=5552421),
    2: dict(beneficiary_2008=116395, beneficiary_2009=114618,
            beneficiary_2010=112845, inpatient=66494, outpatient=792562,
            carrier_a=2372957, carrier_b=2372957, pde=5561154),
}


def parse_samples(value):
    samples = [int(part) for part in value.split(",")]
    if not samples or len(set(samples)) != len(samples) or any(s not in EXPECTED_ROWS for s in samples):
        raise ValueError("Select distinct supported samples (1,2)")
    return samples


def add_samples_argument(parser):
    parser.add_argument("--samples", type=parse_samples,
                        default=parse_samples(os.getenv("MEDICARE_SAMPLES", DEFAULT_SAMPLES)))


def evidence_path(root, stem, sample, suffix="json"):
    name = stem if sample == 1 else f"{stem}_sample_{sample}"
    return Path(root) / "docs" / f"{name}.{suffix}"


def load_profiles(root, samples):
    profiles = [json.loads(evidence_path(root, "data_profile", s).read_text()) for s in samples]
    if [p["sample"] for p in profiles] != samples:
        raise ValueError("Profile sample metadata differs from selected samples")
    return profiles


def missing_hcpcs_paid(profiles):
    """Exact carrier payments in non-HCPCS slots across selected source profiles."""
    return sum((Decimal(v['quirks']['paid_cents_missing_hcpcs']) / 100
                for p in profiles for kind, v in p['files'].items()
                if kind.startswith('carrier')), Decimal(0))
