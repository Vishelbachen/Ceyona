from __future__ import annotations

from typing import Union

from cryptography.fernet import Fernet, InvalidToken

from app.settings import Settings


# =========================
# ENCRYPTION SERVICE
# =========================
class EncryptionService:
    """
    Symmetric encryption layer (Fernet)

    ROLE:
    - encrypt sensitive payloads
    - decrypt encrypted payloads
    - ensure secure transport/storage

    STRICT RULES:
    - no business logic
    - no decision making
    - no interpretation of data
    """

    def __init__(self, settings: Settings):
        self._settings = settings

        key = self._load_key()

        # fail-fast validation at startup (single source)
        self._fernet = Fernet(key)

    # =========================
    # KEY LOADING
    # =========================
    def _load_key(self) -> bytes:
        """
        ENCRYPTION_KEY must be valid Fernet key (base64-encoded 32 bytes).
        """

        key = self._settings.ENCRYPTION_KEY

        if isinstance(key, str):
            key = key.encode("utf-8")

        # minimal safety check (no double initialization)
        if not key:
            raise RuntimeError("ENCRYPTION_KEY is missing")

        return key

    # =========================
    # ENCRYPT
    # =========================
    def encrypt(self, data: Union[str, bytes]) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")

        return self._fernet.encrypt(data).decode("utf-8")

    # =========================
    # DECRYPT
    # =========================
    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")

        except InvalidToken as e:
            raise ValueError("Invalid or corrupted encryption token") from e

    # =========================
    # ROUNDTRIP (DEBUG ONLY)
    # =========================
    def roundtrip(self, data: str) -> str:
        return self.decrypt(self.encrypt(data))