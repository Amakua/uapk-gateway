"""Ed25519 key management for capability token signing."""

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("core.ed25519")


class KeyManagementError(Exception):
    """Raised when key management operations fail."""

    pass


def generate_ed25519_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Generate a new Ed25519 keypair."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def private_key_to_pem(private_key: Ed25519PrivateKey) -> bytes:
    """Serialize private key to PEM format."""
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def public_key_to_pem(public_key: Ed25519PublicKey) -> bytes:
    """Serialize public key to PEM format."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def public_key_to_base64(public_key: Ed25519PublicKey) -> str:
    """Serialize public key to base64-encoded raw bytes."""
    raw_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw_bytes).decode()


def private_key_from_pem(pem_data: bytes) -> Ed25519PrivateKey:
    """Load private key from PEM format."""
    return serialization.load_pem_private_key(pem_data, password=None)  # type: ignore


def public_key_from_pem(pem_data: bytes) -> Ed25519PublicKey:
    """Load public key from PEM format."""
    return serialization.load_pem_public_key(pem_data)  # type: ignore


def public_key_from_base64(b64_data: str) -> Ed25519PublicKey:
    """Load public key from base64-encoded raw bytes."""
    raw_bytes = base64.b64decode(b64_data)
    return Ed25519PublicKey.from_public_bytes(raw_bytes)


class GatewayKeyManager:
    """Manages the gateway's Ed25519 signing keypair.

    In development: generates and stores keys in a volume-mounted directory.
    In production: loads keys from environment variables or secrets.
    """

    _instance: "GatewayKeyManager | None" = None
    _private_key: Ed25519PrivateKey | None = None
    _public_key: Ed25519PublicKey | None = None

    def __new__(cls) -> "GatewayKeyManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._private_key is None:
            self._load_or_generate_keys()

    def _load_or_generate_keys(self) -> None:
        """Load keys from env/file or generate new ones."""
        settings = get_settings()

        # Check for environment variable first (production)
        env_private_key = os.environ.get("GATEWAY_ED25519_PRIVATE_KEY")
        if env_private_key:
            logger.info("loading_gateway_keys_from_env")
            try:
                self._private_key = private_key_from_pem(env_private_key.encode())
                self._public_key = self._private_key.public_key()
                return
            except Exception as e:
                raise KeyManagementError(f"Failed to load private key from env: {e}") from e

        # Development: check for keys in volume-mounted directory
        keys_dir = Path(os.environ.get("GATEWAY_KEYS_DIR", "/app/keys"))

        if not keys_dir.exists():
            keys_dir.mkdir(parents=True, exist_ok=True)

        private_key_path = keys_dir / "gateway_ed25519.pem"
        public_key_path = keys_dir / "gateway_ed25519.pub"

        if private_key_path.exists():
            logger.info("loading_gateway_keys_from_file", path=str(private_key_path))
            try:
                self._private_key = private_key_from_pem(private_key_path.read_bytes())
                self._public_key = self._private_key.public_key()
                return
            except Exception as e:
                logger.warning("failed_to_load_keys", error=str(e))

        # Generate new keys
        logger.info("generating_new_gateway_keys")
        self._private_key, self._public_key = generate_ed25519_keypair()

        # Save to files (development only)
        if settings.environment == "development":
            try:
                private_key_path.write_bytes(private_key_to_pem(self._private_key))
                public_key_path.write_bytes(public_key_to_pem(self._public_key))
                # Set restrictive permissions
                private_key_path.chmod(0o600)
                logger.info(
                    "gateway_keys_saved",
                    private_key_path=str(private_key_path),
                    public_key_path=str(public_key_path),
                )
            except Exception as e:
                logger.warning("failed_to_save_keys", error=str(e))

    @property
    def private_key(self) -> Ed25519PrivateKey:
        """Get the gateway's private key."""
        if self._private_key is None:
            raise KeyManagementError("Private key not initialized")
        return self._private_key

    @property
    def public_key(self) -> Ed25519PublicKey:
        """Get the gateway's public key."""
        if self._public_key is None:
            raise KeyManagementError("Public key not initialized")
        return self._public_key

    @property
    def public_key_base64(self) -> str:
        """Get the gateway's public key as base64."""
        return public_key_to_base64(self.public_key)

    def sign(self, data: bytes) -> bytes:
        """Sign data with the gateway's private key."""
        return self.private_key.sign(data)

    def verify(self, signature: bytes, data: bytes) -> bool:
        """Verify a signature with the gateway's public key."""
        try:
            self.public_key.verify(signature, data)
            return True
        except Exception:
            return False


def get_gateway_key_manager() -> GatewayKeyManager:
    """Get the singleton gateway key manager."""
    return GatewayKeyManager()
