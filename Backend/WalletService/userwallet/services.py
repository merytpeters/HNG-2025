import os
import hmac
import hashlib
import httpx
from typing import Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .crud import WalletCRUD
from WalletService.user.enums import TransactionStatus, TransactionType
from datetime import datetime
from WalletService.user.models import Wallet

PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET")


class WalletService(WalletCRUD):
    def __init__(self):
        super().__init__()

    def initialize_deposit(self, db: Session, user, amount: float, email: str) -> Dict[str, str]:
        if not PAYSTACK_SECRET:
            raise HTTPException(status_code=500, detail="Paystack secret not configured")

        payload = {"amount": int(float(amount) * 100), "email": email}

        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}", "Content-Type": "application/json"}

        resp = httpx.post(PAYSTACK_INIT_URL, json=payload, headers=headers, timeout=15.0)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Paystack init failed: {resp.text}")

        data = resp.json()
        if not data.get("status"):
            raise HTTPException(status_code=400, detail=f"Paystack error: {data}")

        auth = data.get("data") or {}
        reference = auth.get("reference")
        authorization_url = auth.get("authorization_url")

        wallet = self.get_wallet_by_user(db, str(user.id))
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found for user")

        existing = self.get_transaction_by_reference(db, reference)
        if existing:
            raise HTTPException(status_code=400, detail="Duplicate reference")

        tx_data = {
            "transaction_type": TransactionType.DEPOSIT.value,
            "amount": float(amount),
            "reference": reference,
            "transaction_status": TransactionStatus.PENDING.value,
            "authorization_url": authorization_url,
            "wallet_id": wallet.id,
            "walletuser_id": wallet.walletuser_id,
        }

        self.create_transaction(db, tx_data)

        return {"reference": reference, "authorization_url": authorization_url}

    def verify_paystack_signature(self, raw_body: bytes, signature: str) -> bool:
        if not PAYSTACK_SECRET:
            return False
        computed = hmac.new(PAYSTACK_SECRET.encode(), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed, signature)

    def handle_webhook(self, db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:

        event = payload.get("event")
        data = payload.get("data") or {}
        reference = data.get("reference")
        status = data.get("status")
        amount = data.get("amount")

        if reference is None:
            raise HTTPException(status_code=400, detail="Missing reference in webhook")

        tx = self.get_transaction_by_reference(db, reference)
        if not tx:
            return {"status": True, "detail": "transaction not found"}

        if tx.transaction_status == TransactionStatus.SUCCESS.value:
            return {"status": True}

        if status and status.lower() in ("success", "completed", "true"):
            wallet = db.get(Wallet, tx.wallet_id)
            if not wallet:

                self.update_transaction_status(db, tx, TransactionStatus.FAILED.value)
                return {"status": True, "detail": "wallet not found"}

            credited_amount = float(tx.amount)
            self.credit_wallet(db, wallet, credited_amount)
            self.update_transaction_status(db, tx, TransactionStatus.SUCCESS.value)
            return {"status": True}

        self.update_transaction_status(db, tx, TransactionStatus.FAILED.value)
        return {"status": True}

    def verify_deposit_status(self, db: Session, reference: str):
        tx = self.get_transaction_by_reference(db, reference)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return {"reference": tx.reference, "status": tx.transaction_status, "amount": float(tx.amount)}

    def get_balance_for_user(self, db: Session, user_id: str) -> float:
        wallet = self.get_wallet_by_user(db, user_id)
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        return float(wallet.balance)

    def transfer(self, db: Session, sender_wallet, recipient_wallet, amount: float):

        if float(sender_wallet.balance) < float(amount):
            raise HTTPException(status_code=400, detail="Insufficient balance")

        self.debit_wallet(db, sender_wallet, amount)

        self.credit_wallet(db, recipient_wallet, amount)

        sender_tx = {
            "transaction_type": TransactionType.TRANSFER.value,
            "amount": float(amount),
            "reference": f"tx-{datetime.utcnow().timestamp()}-out",
            "transaction_status": TransactionStatus.SUCCESS.value,
            "authorization_url": None,
            "wallet_id": sender_wallet.id,
            "walletuser_id": sender_wallet.walletuser_id,
        }
        recipient_tx = {
            "transaction_type": TransactionType.TRANSFER.value,
            "amount": float(amount),
            "reference": f"tx-{datetime.utcnow().timestamp()}-in",
            "transaction_status": TransactionStatus.SUCCESS.value,
            "authorization_url": None,
            "wallet_id": recipient_wallet.id,
            "walletuser_id": recipient_wallet.walletuser_id,
        }
        self.create_transaction(db, sender_tx)
        self.create_transaction(db, recipient_tx)

        return True
