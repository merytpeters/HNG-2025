from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .apikey_schema import APIKeyCreateSchema
from WalletService.user.models import APIKey


class APIKeyCRUD:
    def __init__(self, model=APIKey):
        self.model = model

    def get(self, db: Session, id):
        return db.get(self.model, id)

    def get_api_key(self, db: Session, id: str):
        if id is None:
            return None
        return db.query(self.model).filter(self.model.id == id).first()

    def create_api_key(self, db: Session, apikey: APIKeyCreateSchema):
        permissions_list = [
            (p.value if getattr(p, "value", None) is not None else p)
            for p in apikey.permissions
        ]
        apikey_data = self.model(
            walletuser_id=apikey.walletuser_id,
            hashed_secret=apikey.secret,
            name=apikey.name,
            permissions=permissions_list,
            expires_at=apikey.expires_at,
            created_at=apikey.created_at,
            revoked=apikey.revoked,
        )
        db.add(apikey_data)
        db.commit()
        db.refresh(apikey_data)
        return apikey_data

    def get_user_api_keys(self, db: Session, user_id: str):
        return db.query(self.model).filter(self.model.walletuser_id == user_id).all()

    def revoke_api_key(self, db: Session, id: str):
        key = self.get_api_key(db, id)
        if not key:
            raise HTTPException(status_code=404, detail="API key not found")
        key.revoked = True  # type: ignore
        db.commit()
        db.refresh(key)
        return key

    def is_api_key_active(self, db: Session, id: str) -> bool:
        key = self.get_api_key(db, id)
        if not key:
            return False

        now = datetime.now(timezone.utc)

        if key.revoked:
            return False

        if not key.expires_at:
            return True

        expires_at = key.expires_at
        if getattr(expires_at, "tzinfo", None) is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return expires_at > now
