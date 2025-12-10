import os
import httpx
import jwt
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from typing import TypeVar, Callable, Any
from user.schemas import GoogleIDTokenSchema, UserCreateOut
from user.models import WalletUser


env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
T = TypeVar("T")


def require_env(name: str, cast: Callable[[str], T] = str) -> T:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"{name} is not set")
    try:
        return cast(value)
    except Exception:
        cast_name = getattr(cast, "__name__", repr(cast))
        raise ValueError(f"{name} could not be cast to {cast_name}")


GOOGLE_ALG = require_env("GOOGLE_ALG")
GOOGLE_CLIENT_ID = require_env("GOOGLE_CLIENT_ID")
JWT_SECRET = require_env("JWT_SECRET")
JWT_EXP_MINUTES = require_env("JWT_EXP_MINUTES", int)
GOOGLE_CLIENT_SECRET = require_env("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = require_env("GOOGLE_REDIRECT_URI")
GOOGLE_TOKEN_URL = require_env("GOOGLE_TOKEN_URL")


class GoogleIDTokenService:
    """Google OAuth Service for Validation and Verification"""

    def validate_email(self, token_schema: GoogleIDTokenSchema) -> bool:
        if "@gmail.com" not in token_schema.email:
            raise ValueError("Email is not a valid google mail")
        return True

    def verify_token(self, token_schema: GoogleIDTokenSchema):
        if token_schema.iss not in [
            "accounts.google.com",
            "https://accounts.google.com",
        ]:
            raise ValueError("Token not issued by Google")
        if token_schema.aud != GOOGLE_CLIENT_ID:
            raise ValueError("Token audience does not match CLIENT ID")
        now = datetime.now(timezone.utc)
        if token_schema.exp < now:
            raise ValueError("Token is expired")
        if not token_schema.email_verified:
            raise ValueError("Email is not verified by Google")
        return "Google ID token verified and email validated successfully."

    def issue_internal_jwt(self, user: WalletUser) -> UserCreateOut:
        payload = {
            "sub": str(user.id),
            "name": user.name,
            "email": user.email,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXP_MINUTES),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        return UserCreateOut(name=user.name, email=user.email, token=token)

    def decode_id_token(self, id_token: str) -> GoogleIDTokenSchema:
        """
        Decode Google ID token without verifying signature (Google signs it).
        """
        decoded = jwt.decode(id_token, options={"verify_signature": False})

        decoded["exp"] = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)

        return GoogleIDTokenSchema(**decoded)

    def exchange_code_for_tokens(self, code: str) -> GoogleIDTokenSchema:
        """
        Exchange Google OAuth authorization code for access and ID token.
        """
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        response = httpx.post(GOOGLE_TOKEN_URL, data=data)

        if response.status_code != 200:
            raise ValueError(f"Failed to exchange token: {response.text}")

        token_data = response.json()

        if "id_token" not in token_data:
            raise ValueError("Google response did not contain id_token")

        id_token = token_data["id_token"]

        return self.decode_id_token(id_token)
