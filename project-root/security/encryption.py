from __future__ import annotations

import base64
from typing import Union

from cryptography.fernet import Fernet

from infra.config_loader import get_settings


settings = get_settings()


# =========================
# ENCRYPTION SERVICE
# =========================
class EncryptionService:
    """
    Symmetric encryption layer (Fernet)

    ROLE:
    - encrypt sensitive payloads
    - decrypt previously encrypted payloads
    - ensure transport/storage safety

    DOES NOT:
    - interpret data
    - modify business logic
    - decide what should be encrypted
    """

    def __init__(self):
        self._fernet = Fernet(self._load_key())

    # =========================
    # KEY HANDLING
    # =========================
    def _load_key(self) -> bytes:
        """
        ENCRYPTION_KEY must be base64-encoded 32-byte key.
        """

        key = settings.ENCRYPTION_KEY

        if isinstance(key, str):
            key = key.encode()

        return key

    # =========================
    # ENCRYPT
    # =========================
    def encrypt(self, data: Union[str, bytes]) -> str:

        if isinstance(data, str):
            data = data.encode("utf-8")

        encrypted = self._fernet.encrypt(data)

        return base64.urlsafe_b64encode(encrypted).decode("utf-8")

    # =========================
    # DECRYPT
    # =========================
    def decrypt(self, token: str) -> str:

        decoded = base64.urlsafe_b64decode(token.encode("utf-8"))

        decrypted = self._fernet.decrypt(decoded)

        return decrypted.decode("utf-8")

    # =========================
    # SAFE ROUNDTRIP CHECK
    # =========================
    def roundtrip(self, data: str) -> str:
        """
        Utility for validation/testing only.
        """

        return self.decrypt(self.encrypt(data))