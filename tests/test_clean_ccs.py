import pytest
from ingest.clean_ccs import normalize, read_map


def test_normalize_preserves_zero_and_letter_codes():
    assert normalize(" '010.00 ' ") == '01000'
    assert normalize(' v10.1 ') == 'V101'
    assert normalize('E800.0') == 'E8000'


def test_clean_header_placeholder_and_duplicate(tmp_path):
    p = tmp_path / 'map.csv'
    p.write_text("Note\n'ICD-9-CM CODE','CCS CATEGORY','CCS CATEGORY DESCRIPTION'\n' ','0','No DX'\n'01000','1 ','Tuberculosis'\n'01000','1','Tuberculosis'\n")
    assert read_map(p) == {'01000': ('1', 'Tuberculosis')}
    p.write_text(p.read_text() + "'01000','2','Conflict'\n")
    with pytest.raises(ValueError, match='Conflicting'):
        read_map(p)


def test_missing_header_rejected(tmp_path):
    p = tmp_path / 'map.csv'
    p.write_text('not a mapping')
    with pytest.raises(ValueError, match='header'):
        read_map(p)
