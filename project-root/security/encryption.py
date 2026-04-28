import hashlib


class EncryptionService:
    """
    Simple hashing abstraction (placeholder for real crypto)
    """

    def hash_data(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()