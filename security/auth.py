from security.jwt import JWTManager


class AuthService:
    def __init__(self, settings, db):
        self.jwt = JWTManager(settings)
        self.db = db

    def login(self, user_id: str) -> str:
        """
        Creates session token
        """
        token = self.jwt.create_token(user_id)

        self.db.insert("sessions", {
            "user_id": user_id,
            "token": token
        })

        return token

    def verify(self, token: str) -> dict:
        decoded = self.jwt.decode_token(token)

        if "error" in decoded:
            return {"valid": False, "reason": decoded["error"]}

        return {"valid": True, "user_id": decoded["user_id"]}