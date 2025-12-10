from fastapi import APIRouter, Depends, HTTPException
from urllib.parse import urlencode
import os
from sqlalchemy.orm import Session
from .schemas import UserCreateOut
from db import get_session
from .user_service import UserService
from .models import WalletUser
from WalletService.auth.service import GoogleIDTokenService


router = APIRouter(prefix="/auth", tags=["Google OAuth2.0"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
GOOGLE_SCOPE = "openid email profile"

user_service = UserService(WalletUser)
google_service = GoogleIDTokenService()


@router.get("/google")
def google_login():
    """
    Redirect user to Google OAuth consent page.
    """
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    )
    return {"auth_url": google_auth_url}


@router.get("/google/callback", response_model=UserCreateOut)
async def google_callback(code: str, db: Session = Depends(get_session)):
    """
    Google redirects here with ?code=...
    You exchange the code for tokens, verify ID token, create/get user, return JWT.
    """
    try:

        google_token = google_service.exchange_code_for_tokens(code)

        user_out = user_service.create_or_get_user(google_token, db)
        return user_out

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
