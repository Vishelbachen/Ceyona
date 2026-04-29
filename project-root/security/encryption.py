import base64
from cryptography.fernet import Fernet
from app.settings import settings


def _get_fernet() -> Fernet:
    key = settings.encryption_key.encode()
    if len(key) != 44:
        key = base64.urlsafe_b64encode(key[:32].ljust(32, b"="))
    return Fernet(key)


def encrypt(text: str) -> str:
    return _get_fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()