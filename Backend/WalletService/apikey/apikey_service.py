import re
from datetime import datetime, timezone, timedelta
from typing import Type, cast, List, Dict
import calendar
import secrets
import os
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .apikey_crud import APIKeyCRUD
from .apikey_schema import APIKeyCreateSchema, APIKeyOut
from WalletService.user.models import APIKey
from WalletService.user.enums import APIKey_Permissions
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Load env
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
try:
    APIKEY_EXPIRATION_DAYS = int(os.getenv("APIKEY_EXPIRATION_DAYS", "30"))
except ValueError:
    raise ValueError("APIKEY_EXPIRATION_DAYS must be an integer")


class APIKeyService(APIKeyCRUD):
    def __init__(self, model: Type[APIKey] = APIKey):
        super().__init__(cast(Type[APIKey], model))

    def revoke_key(self, db: Session, key_id: str) -> APIKeyOut:
        key = self.revoke_api_key(db, key_id)
        return APIKeyOut(
            walletuser_id=str(key.walletuser_id),
            name=str(key.name),
            permissions=list(key.permissions),
            expires_at=key.expires_at,
            created_at=key.created_at,
            revoked=key.revoked,
        )

    def is_key_active(self, db: Session, key_id: str) -> bool:
        return self.is_api_key_active(db, key_id)

    def list_user_keys(self, db: Session, user_id: str) -> List[APIKeyOut]:
        keys = self.get_user_api_keys(db, user_id)
        return [
            APIKeyOut(
                walletuser_id=str(k.walletuser_id),
                name=str(k.name),
                permissions=list(k.permissions),
                expires_at=k.expires_at,
                created_at=k.created_at,
                revoked=k.revoked,
            )
            for k in keys
        ]

    def _parse_expiry(self, expiry: str, from_dt: datetime | None = None) -> datetime:
        if from_dt is None:
            from_dt = datetime.now(timezone.utc)
        expiry = expiry.upper().strip()
        
        match = re.fullmatch(r"(\d+)([HDMY])", expiry)
        if not match:
            raise HTTPException(
                status_code=400,
                detail="expiry must follow format: <number><H|D|M|Y> e.g., 2H, 10D, 3M, 1Y",
            )

        value, unit = match.groups()
        value = int(value)
        if unit == "H":
            return from_dt + timedelta(hours=value)
        if unit == "D":
            return from_dt + timedelta(days=value)
        if unit == "M":
            year = from_dt.year
            month = from_dt.month + value
            year += (month - 1) // 12
            month = ((month - 1) % 12) + 1

            day = min(from_dt.day, calendar.monthrange(year, month)[1])
            return datetime(
                year, month, day,
                from_dt.hour, from_dt.minute, from_dt.second,
                tzinfo=timezone.utc
            )

        if unit == "Y":
            year = from_dt.year + value
            month = from_dt.month
            day = min(from_dt.day, calendar.monthrange(year, month)[1])
            return datetime(
                year, month, day,
                from_dt.hour, from_dt.minute, from_dt.second,
                tzinfo=timezone.utc
            )

    def _generate_secret(self) -> str:
        return "sk_live_" + secrets.token_urlsafe(24)

    def create_key_with_expiry(
        self, db: Session, user_id: str, name: str, permissions: List[str], expiry: str
    ) -> Dict[str, str]:
        if not permissions:
            raise HTTPException(status_code=400, detail="Permissions must be provided")

        # Max 5 active keys
        active_count = sum(
            1
            for k in self.get_user_api_keys(db, user_id)
            if self.is_api_key_active(db, str(k.id))
        )
        if active_count >= 5:
            raise HTTPException(
                status_code=400, detail="Maximum of 5 active API keys per user exceeded"
            )

        now = datetime.now(timezone.utc)
        expires_at = self._parse_expiry(expiry, now)

        perms_enum = [
            p if isinstance(p, APIKey_Permissions) else APIKey_Permissions(p)
            for p in permissions
        ]

        api_secret = self._generate_secret()
        hashed = pwd.hash(api_secret)

        key_schema = APIKeyCreateSchema(
            walletuser_id=user_id,
            name=name,
            secret=hashed,
            permissions=perms_enum,
            created_at=now,
            expires_at=expires_at,
            revoked=False,
        )

        key_record = self.create_api_key(db, key_schema)

        expires_at_str = expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"api_key": api_secret, "expires_at": expires_at_str}

    def rollover_key(
        self, db: Session, expired_key_id: str, expiry: str
    ) -> Dict[str, str]:
        old_key = self.get_api_key(db, expired_key_id)
        if not old_key:
            raise HTTPException(status_code=404, detail="Expired key not found")

        if self.is_api_key_active(db, expired_key_id):
            raise HTTPException(
                status_code=400, detail="Key is not expired and cannot be rolled over"
            )

        secret = self._generate_secret()
        hashed = pwd.hash(secret)
        expires_at = self._parse_expiry(expiry)
        key_schema = APIKeyCreateSchema(
            walletuser_id=str(old_key.walletuser_id),
            secret=hashed,
            name=f"{old_key.name}-rollover",
            permissions=list(old_key.permissions),
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            revoked=False,
        )
        new_key_record = self.create_api_key(db, key_schema)
        expires_at_str = expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"api_key": secret, "expires_at": expires_at_str}
