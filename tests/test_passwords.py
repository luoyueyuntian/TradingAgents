import hashlib

import pytest

from web.passwords import (
    generate_verification_code,
    hash_password,
    hash_secret,
    validate_password_policy,
    verify_password,
)


def test_password_hash_verifies_original_password():
    stored = hash_password("StrongerPass123!")

    assert verify_password("StrongerPass123!", stored.encoded_hash, stored.salt)
    assert not verify_password("wrong-password", stored.encoded_hash, stored.salt)


def test_password_hash_uses_unique_salts():
    first = hash_password("StrongerPass123!")
    second = hash_password("StrongerPass123!")

    assert first.salt != second.salt
    assert first.encoded_hash != second.encoded_hash


def test_password_policy_rejects_too_short_password():
    with pytest.raises(ValueError, match="at least 8 characters"):
        validate_password_policy("Aa1!", username="trader", email="trader@example.com")


def test_password_policy_rejects_whitespace_only_password():
    with pytest.raises(ValueError, match="must not be blank"):
        validate_password_policy("        ", username="trader", email="trader@example.com")


def test_password_policy_rejects_password_matching_username():
    with pytest.raises(ValueError, match="must not match username"):
        validate_password_policy(
            "StockTrader1",
            username="stocktrader1",
            email="trader@example.com",
        )


def test_password_policy_rejects_password_matching_email():
    with pytest.raises(ValueError, match="must not match email"):
        validate_password_policy(
            "person123@example.com",
            username="trader",
            email="PERSON123@example.com",
        )


@pytest.mark.parametrize("password", ["alllowercase", "12345678", "!!!!!!!!"])
def test_password_policy_requires_at_least_two_character_classes(password):
    with pytest.raises(ValueError, match="at least two character classes"):
        validate_password_policy(password, username="trader", email="trader@example.com")


def test_password_policy_accepts_password_with_two_character_classes():
    validate_password_policy("longpassword1", username="trader", email="trader@example.com")


def test_generate_verification_code_returns_zero_padded_six_digit_code(monkeypatch):
    def fake_randbelow(upper_bound):
        assert upper_bound == 1_000_000
        return 42

    monkeypatch.setattr("web.passwords.secrets.randbelow", fake_randbelow)

    assert generate_verification_code() == "000042"


def test_hash_secret_returns_sha256_hex_digest():
    assert hash_secret("verify-me") == hashlib.sha256(b"verify-me").hexdigest()
