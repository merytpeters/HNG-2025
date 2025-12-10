from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional, List
from user.models import Wallet, Transaction


class WalletCRUD:
    def __init__(self, wallet_model=Wallet, tx_model=Transaction):
        self.wallet_model = wallet_model
        self.tx_model = tx_model

    def get_wallet_by_user(self, db: Session, user_id: str) -> Optional[Wallet]:
        return db.query(self.wallet_model).filter(self.wallet_model.walletuser_id == user_id).first()

    def get_wallet_by_number(self, db: Session, wallet_number: int) -> Optional[Wallet]:
        return db.query(self.wallet_model).filter(self.wallet_model.wallet_number == wallet_number).first()

    def get_transaction_by_reference(self, db: Session, reference: str) -> Optional[Transaction]:
        return db.query(self.tx_model).filter(self.tx_model.reference == reference).first()

    def create_transaction(self, db: Session, tx_data: dict) -> Transaction:
        tx = self.tx_model(**tx_data)
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    def update_transaction_status(self, db: Session, tx: Transaction, status: str) -> Transaction:
        tx.transaction_status = status
        db.commit()
        db.refresh(tx)
        return tx

    def credit_wallet(self, db: Session, wallet: Wallet, amount: float) -> Wallet:
        wallet.balance = float(wallet.balance) + float(amount)
        db.commit()
        db.refresh(wallet)
        return wallet

    def debit_wallet(self, db: Session, wallet: Wallet, amount: float) -> Wallet:
        if float(wallet.balance) < float(amount):
            raise HTTPException(status_code=400, detail="Insufficient balance")
        wallet.balance = float(wallet.balance) - float(amount)
        db.commit()
        db.refresh(wallet)
        return wallet

    def list_transactions_for_user(self, db: Session, user_id: str) -> List[Transaction]:
        return db.query(self.tx_model).filter(self.tx_model.walletuser_id == user_id).order_by(self.tx_model.id.desc()).all()
