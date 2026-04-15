from cryptography.fernet import Fernet


class Encryption:
    def __init__(self, settings):
        self.key = settings.ENCRYPTION_KEY
        self.cipher = Fernet(self.key.encode())

    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self.cipher.decrypt(token.encode()).decode()