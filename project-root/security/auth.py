class AuthService:
    """
    Minimal auth layer (token-based mock)
    """

    def verify_token(self, token: str) -> bool:
        return token is not None and len(token) > 10

    def get_user_id(self, token: str) -> str:
        return f"user_{hash(token) % 10000}"