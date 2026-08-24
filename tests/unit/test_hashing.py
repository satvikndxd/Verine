import math

import pytest

from verine.common.hashing import canonical_json, hash_obj


def test_key_order_invariance():
    a = {"b": 1, "a": [{"y": 2, "x": 3}]}
    b = {"a": [{"x": 3, "y": 2}], "b": 1}
    assert hash_obj(a) == hash_obj(b)


def test_value_sensitivity():
    assert hash_obj({"a": 1}) != hash_obj({"a": 2})


def test_nan_rejected():
    with pytest.raises(ValueError):
        canonical_json({"a": math.nan})
    with pytest.raises(ValueError):
        canonical_json({"a": math.inf})


def test_non_string_key_rejected():
    with pytest.raises(ValueError):
        canonical_json({1: "a"})


def test_hash_prefix():
    assert hash_obj({}).startswith("sha256:")
