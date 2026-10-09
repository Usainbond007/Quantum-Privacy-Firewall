import json
import pytest
from qpf.artifact_integrity import (digest, file_sha256, provenance,
    write_json_atomic, require_matching_cache, validate_unique_keys)

def test_fingerprint_deterministic():
    assert digest({'a': 1, 'b': 2}) == digest({'b': 2, 'a': 1})
    assert digest({'a': 1}) != digest({'a': 2})

def test_cache_fail_closed(tmp_path):
    p = tmp_path / 'cache.json'
    with pytest.raises(ValueError, match='missing'):
        require_matching_cache(p, {'schema': 1})
    write_json_atomic(p, {'schema': 1})
    assert require_matching_cache(p, {'schema': 1})
    with pytest.raises(ValueError, match='mismatch'):
        require_matching_cache(p, {'schema': 2})

def test_duplicate_keys_rejected():
    assert validate_unique_keys([{'id': 1}, {'id': 2}], ['id']) == 2
    with pytest.raises(ValueError, match='Duplicate'):
        validate_unique_keys([{'id': 1}, {'id': 1}], ['id'])

def test_source_change_invalidates(tmp_path):
    src = tmp_path / 'src.py'
    src.write_text('a=1')
    a = provenance({'seed': 7}, [src])
    src.write_text('a=2')
    assert provenance({'seed': 7}, [src]) != a
