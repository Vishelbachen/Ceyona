import base64
import logging

from cryptography.fernet import Fernet

from app.settings import settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = settings.encryption_key
    if len(key) < 32:
        key = key.ljust(32, "0")
    b64 = base64.urlsafe_b64encode(key[:32].encode())
    return Fernet(b64)


def encrypt(plaintext: str) -> str:
    """Encrypt string. Returns base64-encoded ciphertext."""
    try:
        f = _get_fernet()
        return f.encrypt(plaintext.encode()).decode()
    except Exception as exc:
        logger.error("Encryption failed", extra={"error": str(exc)})
        raise


def decrypt(ciphertext: str) -> str:
    """Decrypt base64-encoded ciphertext. Returns plaintext."""
    try:
        f = _get_fernet()
        return f.decrypt(ciphertext.encode()).decode()
    except Exception as exc:
        logger.error("Decryption failed", extra={"error": str(exc)})
        raise