import hmac
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from user.models import Base, WalletUser, Wallet, Transaction
from userwallet.services import WalletService, PAYSTACK_SECRET
import os


def create_in_memory_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_verify_paystack_signature():
    svc = WalletService()
    # patch secret
    svc_secret = "test_secret"
    # set module level var
    import userwallet.services as services_module

    services_module.PAYSTACK_SECRET = svc_secret

    raw = b'{"hello":"world"}'
    signature = hmac.new(svc_secret.encode(), raw, hashlib.sha512).hexdigest()
    assert svc.verify_paystack_signature(raw, signature) is True


def test_handle_webhook_success_idempotent():
    db = create_in_memory_db()
    svc = WalletService()

    user = WalletUser(name="Alice", email="alice@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    wallet = Wallet(balance=10000.0, wallet_number=1111, walletuser_id=user.id)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)

    tx = Transaction(
        transaction_type="deposit",
        amount=5000.0,
        reference="ref-123",
        transaction_status="pending",
        authorization_url=None,
        wallet_id=wallet.id,
        walletuser_id=user.id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    payload = {
        "event": "charge.success",
        "data": {"reference": "ref-123", "status": "success", "amount": 500000},
    }

    res = svc.handle_webhook(db, payload)
    db.refresh(wallet)
    db.refresh(tx)
    assert wallet.balance == 15000.0
    assert tx.transaction_status == "success"
    assert res.get("status") is True

    res2 = svc.handle_webhook(db, payload)
    db.refresh(wallet)
    assert wallet.balance == 15000.0
    assert res2.get("status") is True


def test_transfer_atomic():
    db = create_in_memory_db()
    svc = WalletService()

    sender = WalletUser(name="Bob", email="bob@example.com")
    recipient = WalletUser(name="Carol", email="carol@example.com")
    db.add_all([sender, recipient])
    db.commit()
    db.refresh(sender)
    db.refresh(recipient)

    sw = Wallet(balance=10000.0, wallet_number=2222, walletuser_id=sender.id)
    rw = Wallet(balance=2000.0, wallet_number=3333, walletuser_id=recipient.id)
    db.add_all([sw, rw])
    db.commit()
    db.refresh(sw)
    db.refresh(rw)

    svc.transfer(db, sw, rw, 3000.0)

    db.refresh(sw)
    db.refresh(rw)
    assert sw.balance == 7000.0
    assert rw.balance == 5000.0

    # ensure two transaction records were created
    txs_sender = db.query(Transaction).filter(Transaction.wallet_id == sw.id).all()
    txs_recipient = db.query(Transaction).filter(Transaction.wallet_id == rw.id).all()
    assert len(txs_sender) == 1
    assert len(txs_recipient) == 1
