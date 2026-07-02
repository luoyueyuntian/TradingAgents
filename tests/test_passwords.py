import base64
import hashlib

import pytest

from web.passwords import (
    PBKDF2_ITERATIONS,
    VERIFICATION_CODE_HASH_PREFIX,
    VERIFICATION_CODE_PBKDF2_ITERATIONS,
    generate_verification_code,
    hash_password,
    hash_secret,
    hash_verification_code,
    validate_password_policy,
    verify_password,
    verify_verification_code,
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


def test_pbkdf2_iterations_match_security_policy():
    assert PBKDF2_ITERATIONS == 260_000


def test_hash_password_uses_pbkdf2_hmac_sha256_iterations_and_16_byte_salt(monkeypatch):
    captured = {}

    def fake_token_bytes(length):
        captured["salt_length"] = length
        return b"x" * length

    def fake_pbkdf2_hmac(algorithm, password_bytes, salt_bytes, iterations):
        captured["algorithm"] = algorithm
        captured["password_bytes"] = password_bytes
        captured["salt_bytes"] = salt_bytes
        captured["iterations"] = iterations
        return b"derived-digest"

    monkeypatch.setattr("web.passwords.secrets.token_bytes", fake_token_bytes)
    monkeypatch.setattr("web.passwords.hashlib.pbkdf2_hmac", fake_pbkdf2_hmac)

    stored = hash_password("StrongerPass123!")

    assert captured == {
        "algorithm": "sha256",
        "password_bytes": b"StrongerPass123!",
        "salt_bytes": b"x" * 16,
        "salt_length": 16,
        "iterations": PBKDF2_ITERATIONS,
    }
    assert stored.salt == base64.b64encode(b"x" * 16).decode("ascii")
    assert stored.encoded_hash == base64.b64encode(b"derived-digest").decode("ascii")


def test_verify_password_uses_compare_digest(monkeypatch):
    calls = []

    def fake_pbkdf2_hmac(algorithm, password_bytes, salt_bytes, iterations):
        assert algorithm == "sha256"
        assert password_bytes == b"StrongerPass123!"
        assert salt_bytes == b"x" * 16
        assert iterations == PBKDF2_ITERATIONS
        return b"computed-digest"

    def fake_compare_digest(left, right):
        calls.append((left, right))
        return True

    monkeypatch.setattr("web.passwords.hashlib.pbkdf2_hmac", fake_pbkdf2_hmac)
    monkeypatch.setattr("web.passwords.secrets.compare_digest", fake_compare_digest)

    assert verify_password(
        "StrongerPass123!",
        base64.b64encode(b"stored-digest").decode("ascii"),
        base64.b64encode(b"x" * 16).decode("ascii"),
    )
    assert calls


@pytest.mark.parametrize("salt", ["not-base64!", "not-base64\u2603"])
def test_verify_password_returns_false_for_invalid_salt(salt):
    stored = hash_password("StrongerPass123!")

    assert not verify_password("StrongerPass123!", stored.encoded_hash, salt)


def test_verify_password_returns_false_for_base64_valid_wrong_length_salt():
    wrong_salt = b"short"
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        b"StrongerPass123!",
        wrong_salt,
        PBKDF2_ITERATIONS,
    )

    assert not verify_password(
        "StrongerPass123!",
        base64.b64encode(digest).decode("ascii"),
        base64.b64encode(wrong_salt).decode("ascii"),
    )


@pytest.mark.parametrize("encoded_hash", ["not-base64!", "not-base64\u2603"])
def test_verify_password_returns_false_for_invalid_encoded_hash(encoded_hash):
    stored = hash_password("StrongerPass123!")

    assert not verify_password("StrongerPass123!", encoded_hash, stored.salt)


def test_password_policy_rejects_too_short_password():
    with pytest.raises(ValueError, match="at least 10 characters"):
        validate_password_policy("Abcdefgh1", username="trader", email="trader@example.com")


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


@pytest.mark.parametrize("password", ["alllowercase", "1234567890", "!!!!!!!!!!"])
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


def test_hash_verification_code_uses_salted_pbkdf2_and_verifies_code():
    first = hash_verification_code("123456")
    second = hash_verification_code("123456")

    assert first != second
    assert first.startswith(f"{VERIFICATION_CODE_HASH_PREFIX}$")
    assert f"${VERIFICATION_CODE_PBKDF2_ITERATIONS}$" in first
    assert first != hashlib.sha256(b"123456").hexdigest()
    assert verify_verification_code("123456", first)
    assert not verify_verification_code("000000", first)


@pytest.mark.parametrize(
    "encoded_hash",
    [
        "",
        "not-a-reset-code-hash",
        "pbkdf2_sha256$not-an-int$salt$digest",
        "pbkdf2_sha256$1$c2FsdA==$ZGlnZXN0",
        "pbkdf2_sha256$260000$not-base64!$ZGlnZXN0",
    ],
)
def test_verify_verification_code_rejects_malformed_hashes(encoded_hash):
    assert not verify_verification_code("123456", encoded_hash)


def test_hash_secret_returns_sha256_hex_digest_for_high_entropy_secret():
    secret = "f0b49181893b4bb48b3048e9b6e9ef94"

    assert hash_secret(secret) == hashlib.sha256(secret.encode("utf-8")).hexdigest()


def test_hash_secret_docstring_warns_against_low_entropy_verification_codes():
    docstring = hash_secret.__doc__ or ""

    assert "high-entropy" in docstring
    assert "low-entropy" in docstring
    assert "verification codes" in docstring
