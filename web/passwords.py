import base64
import binascii
import hashlib
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordHash:
    encoded_hash: str
    salt: str


PBKDF2_ITERATIONS = 260_000
SALT_BYTES = 16


def hash_password(password: str) -> PasswordHash:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return PasswordHash(
        encoded_hash=base64.b64encode(digest).decode("ascii"),
        salt=base64.b64encode(salt).decode("ascii"),
    )


def _decode_base64_ascii(value: str) -> bytes | None:
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error):
        return None


def verify_password(password: str, encoded_hash: str, salt: str) -> bool:
    salt_bytes = _decode_base64_ascii(salt)
    stored_digest = _decode_base64_ascii(encoded_hash)
    if salt_bytes is None or stored_digest is None:
        return False
    if len(salt_bytes) != SALT_BYTES:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        PBKDF2_ITERATIONS,
    )
    return secrets.compare_digest(digest, stored_digest)


def validate_password_policy(password: str, *, username: str, email: str) -> None:
    if not password.strip():
        raise ValueError("Password must not be blank")
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters")

    normalized_password = password.casefold()
    if normalized_password == username.casefold():
        raise ValueError("Password must not match username")
    if normalized_password == email.casefold():
        raise ValueError("Password must not match email")

    character_classes = sum(
        (
            any(character.islower() for character in password),
            any(character.isupper() for character in password),
            any(character.isdigit() for character in password),
            any(not character.isalnum() for character in password),
        )
    )
    if character_classes < 2:
        raise ValueError("Password must include at least two character classes")


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_secret(value: str) -> str:
    """Hash a high-entropy secret; do not use for low-entropy verification codes."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
