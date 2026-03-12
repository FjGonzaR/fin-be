import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from jwt_secret using SHA-256."""
    raw = hashlib.sha256(settings.jwt_secret.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt_password(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a URL-safe base64 token."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_password(token: str) -> str:
    """Decrypt a token produced by encrypt_password."""
    return _get_fernet().decrypt(token.encode()).decode()
