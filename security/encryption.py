from cryptography.fernet import Fernet


class Encryption:
    def __init__(self, settings):
        key = settings.ENCRYPTION_KEY

        # ensure correct type
        if isinstance(key, str):
            key = key.encode()

        self.cipher = Fernet(key)

    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self.cipher.decrypt(token.encode()).decode()