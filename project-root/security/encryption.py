from cryptography.fernet import Fernet
from app.settings import settings


def _fernet() -> Fernet:
    return Fernet(settings.encryption_key.encode())


def encrypt(text: str) -> str:
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()