from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Union, Optional
from jose import JWTError, jwt
from pathlib import Path
from dotenv import load_dotenv
from WalletService.user.models import WalletUser, APIKey
from WalletService.user.crud import UserCRUD
from db import get_session
from WalletService.apikey.apikey_service import APIKeyService
import os


env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

user_crud = UserCRUD(WalletUser)
apikey_service = APIKeyService()

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM") or "HS256"


def get_current_identity(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_session),
) -> Union[WalletUser, APIKey]:
    """
    Returns either:
    - WalletUser if JWT is provided
    - APIKey if x-api-key is provided
    """
    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid Authorization header")
        token = authorization[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id: str = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Token missing sub")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid JWT token")

        user = user_crud.get(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    if x_api_key:
        key = apikey_service.get_api_key_by_secret(db, x_api_key)
        if not key or not apikey_service.is_key_active(db, key.id):
            raise HTTPException(status_code=401, detail="Invalid or expired API key")
        return key

    raise HTTPException(
        status_code=401, detail="No authentication credentials provided"
    )
