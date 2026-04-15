import jwt
import datetime
from typing import Dict, Any


class JWTManager:
    def __init__(self, settings):
        self.secret = settings.JWT_SECRET
        self.algorithm = "HS256"

    def create_token(self, user_id: str, expires_minutes: int = 60) -> str:
        payload = {
            "user_id": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_minutes),
            "iat": datetime.datetime.utcnow()
        }

        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return {"error": "token_expired"}
        except jwt.InvalidTokenError:
            return {"error": "invalid_token"}