from __future__ import annotations

from typing import Union
from cryptography.fernet import Fernet


# =========================
# ENCRYPTION SERVICE
# =========================
class EncryptionService:
    """
    Symmetric encryption layer (Fernet)

    ROLE:
    - encrypt sensitive payloads
    - decrypt payloads
    - protect storage & transport data

    DOES NOT:
    - interpret data
    - decide encryption policy
    - modify business logic
    """

    def __init__(self, encryption_key: str):
        """
        encryption_key must be base64-encoded Fernet key
        """
        self._fernet = Fernet(encryption_key.encode())

    # =========================
    # ENCRYPT
    # =========================
    def encrypt(self, data: Union[str, bytes]) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")

        encrypted = self._fernet.encrypt(data)

        return encrypted.decode("utf-8")

    # =========================
    # DECRYPT
    # =========================
    def decrypt(self, token: str) -> str:
        decrypted = self._fernet.decrypt(token.encode("utf-8"))
        return decrypted.decode("utf-8")

    # =========================
    # ROUNDTRIP TEST
    # =========================
    def roundtrip(self, data: str) -> str:
        return self.decrypt(self.encrypt(data))