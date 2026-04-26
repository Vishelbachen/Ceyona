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
    - ensure secure storage/transport

    STRICT RULES:
    - no business logic
    - no decision making
    - no data interpretation
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._fernet = Fernet(self._load_key())

    # =========================
    # KEY LOADING
    # =========================
    def _load_key(self) -> bytes:
        """
        ENCRYPTION_KEY must be a valid Fernet key:
        base64-encoded 32-byte key
        """

        key = self._settings.ENCRYPTION_KEY

        if isinstance(key, str):
            key = key.encode()

        # basic validation (fail-fast)
        try:
            Fernet(key)
        except Exception as e:
            raise RuntimeError(
                "Invalid ENCRYPTION_KEY. Must be valid Fernet key."
            ) from e

        return key

    # =========================
    # ENCRYPT
    # =========================
    def encrypt(self, data: Union[str, bytes]) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")

        # Fernet already returns base64-safe token
        return self._fernet.encrypt(data).decode("utf-8")

    # =========================
    # DECRYPT
    # =========================
    def decrypt(self, token: str) -> str:
        try:
            decrypted = self._fernet.decrypt(token.encode("utf-8"))
            return decrypted.decode("utf-8")

        except InvalidToken as e:
            raise ValueError("Invalid or corrupted encryption token") from e

    # =========================
    # ROUNDTRIP TEST (DEBUG ONLY)
    # =========================
    def roundtrip(self, data: str) -> str:
        return self.decrypt(self.encrypt(data))