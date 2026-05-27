import hmac
import hashlib
import json
from datetime import timezone
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from WalletService.user.models import Base, WalletUser, Wallet, Transaction
from WalletService.userwallet import routes as wallet_routes
from WalletService.userwallet import services as wallet_services_module
from db import get_session


def create_in_memory_db():
    # Use a temporary file-backed SQLite DB with check_same_thread=False so
    # the TestClient (which runs requests in a different thread) can access it.
    engine = create_engine(
        "sqlite:///./test_webhook.db",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_paystack_webhook_updates_tx_and_credits_wallet():
    # prepare in-memory DB and session override
    db = create_in_memory_db()

    # create user, wallet, and pending transaction
    user = WalletUser(name="Alice", email="alice@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    wallet = Wallet(balance=1000.0, wallet_number=1111, walletuser_id=user.id)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)

    tx = Transaction(
        transaction_type="deposit",
        amount=250.0,
        reference="ref-integ-1",
        transaction_status="pending",
        authorization_url=None,
        wallet_id=wallet.id,
        walletuser_id=user.id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # mount router in a fresh app WITHOUT the global API auth dependency
    app = FastAPI()

    app.include_router(wallet_routes.router)

    def _get_test_session():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_session] = _get_test_session

    svc_secret = "test_secret"
    wallet_services_module.PAYSTACK_SECRET = svc_secret

    client = TestClient(app)

    payload = {
        "event": "charge.success",
        "data": {"reference": "ref-integ-1", "status": "success", "amount": 25000},
    }

    payload_str = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(
        svc_secret.encode(), payload_str.encode(), hashlib.sha512
    ).hexdigest()

    headers = {"x-paystack-signature": sig, "Content-Type": "application/json"}

    resp = client.post("/wallet/paystack/webhook", content=payload_str, headers=headers)

    assert resp.status_code in (200, 201)

    # refresh DB objects and assert wallet was credited and tx marked success
    db.refresh(wallet)
    db.refresh(tx)
    assert cast(Any, wallet.balance) == 1250.0
    assert cast(Any, tx.transaction_status) == "success"
