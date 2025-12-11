from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .models import WalletUser
from .schemas import GoogleIDTokenSchema
import random
from .models import Wallet


class UserCRUD:
    def __init__(self, model):
        self.model = model

    def get(self, session: Session, id):
        return session.get(self.model, id)

    async def get_user_by_id(self, user_id: str, db: Session):
        user = db.get(WalletUser, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def get_by_google_sub(self, db: Session, google_sub: Optional[str]):
        if google_sub is None:
            return None
        return db.query(self.model).filter(self.model.google_sub == google_sub).first()

    def get_or_create_by_google_token(
        self, db: Session, google_token: GoogleIDTokenSchema
    ):
        user = self.get_by_google_sub(db, google_token.sub)
        if not user:
            if google_token.sub is None:
                raise HTTPException(
                    status_code=400, detail="Missing google sub in token"
                )
            obj_data = {
                "name": google_token.name,
                "email": google_token.email,
                "google_sub": google_token.sub,
            }
            user = self.create(db, obj_data)

            def _generate_wallet_number():
                while True:
                    num = random.randint(10**9, 10**10 - 1)
                    existing = (
                        db.query(Wallet).filter(Wallet.wallet_number == num).first()
                    )
                    if not existing:
                        return num

            wallet = Wallet(
                balance=0.0,
                wallet_number=_generate_wallet_number(),
                walletuser_id=user.id,
            )
            db.add(wallet)
            db.commit()
            db.refresh(wallet)
        return user

    def create(self, session: Session, obj_data: dict):
        obj = self.model(**obj_data)
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj
