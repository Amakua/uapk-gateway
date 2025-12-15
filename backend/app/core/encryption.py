"""Fernet encryption utilities for secret storage."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""

    pass


def get_fernet() -> Fernet:
    """Get Fernet instance from settings.

    Raises:
        EncryptionError: If GATEWAY_FERNET_KEY is not configured.
    """
    settings = get_settings()
    if not settings.gateway_fernet_key:
        raise EncryptionError(
            "GATEWAY_FERNET_KEY is not configured. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )

    try:
        return Fernet(settings.gateway_fernet_key.encode())
    except Exception as e:
        raise EncryptionError(f"Invalid GATEWAY_FERNET_KEY: {e}") from e


def encrypt_value(plaintext: str) -> bytes:
    """Encrypt a string value using Fernet.

    Args:
        plaintext: The string to encrypt

    Returns:
        Encrypted bytes

    Raises:
        EncryptionError: If encryption fails
    """
    try:
        fernet = get_fernet()
        return fernet.encrypt(plaintext.encode())
    except EncryptionError:
        raise
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {e}") from e


def decrypt_value(ciphertext: bytes) -> str:
    """Decrypt a Fernet-encrypted value.

    Args:
        ciphertext: The encrypted bytes

    Returns:
        Decrypted string

    Raises:
        EncryptionError: If decryption fails
    """
    try:
        fernet = get_fernet()
        return fernet.decrypt(ciphertext).decode()
    except EncryptionError:
        raise
    except InvalidToken:
        raise EncryptionError("Invalid ciphertext or wrong encryption key")
    except Exception as e:
        raise EncryptionError(f"Decryption failed: {e}") from e


def generate_fernet_key() -> str:
    """Generate a new Fernet key.

    Returns:
        Base64-encoded Fernet key string
    """
    return Fernet.generate_key().decode()
