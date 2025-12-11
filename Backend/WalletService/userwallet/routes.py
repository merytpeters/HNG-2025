import json
import logging
from fastapi import APIRouter, Depends, Request, HTTPException, Header
from sqlalchemy.orm import Session
from db import get_session
from WalletService.auth.jwt import get_current_identity
from .schemas import (
    DepositRequest,
    DepositInitOut,
    DepositStatusOut,
    BalanceOut,
    TransferRequest,
    SimpleOut,
    TransactionListOut,
)
from .services import WalletService
from WalletService.user.models import APIKey

router = APIRouter(prefix="/wallet", tags=["wallet"])
public_router = APIRouter(prefix="/wallet", tags=["wallet-public"])

service = WalletService()

# logger for this module
logger = logging.getLogger(__name__)


def _identity_to_user_id(identity):
    if hasattr(identity, "id") and getattr(identity, "email", None):
        return str(identity.id)
    if isinstance(identity, APIKey) or hasattr(identity, "walletuser_id"):
        return str(identity.walletuser_id)
    raise HTTPException(status_code=401, detail="Invalid identity")


def _has_permission_identity(identity, perm: str) -> bool:
    if hasattr(identity, "email"):
        return True
    perms = getattr(identity, "permissions", []) or []
    return perm in perms


@router.post("/deposit", response_model=DepositInitOut)
def deposit(
    req: DepositRequest,
    identity=Depends(get_current_identity),
    db: Session = Depends(get_session),
):
    if not _has_permission_identity(identity, "deposit"):
        raise HTTPException(
            status_code=403, detail="API key missing deposit permission"
        )

    user_id = _identity_to_user_id(identity)
    email = getattr(identity, "email", None)
    if not email:
        from user.crud import UserCRUD

        user_crud = UserCRUD(None)
        user = user_crud.get(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        email = user.email

    out = service.initialize_deposit(db, identity, req.amount, email)
    return DepositInitOut(
        reference=out["reference"], authorization_url=out["authorization_url"]
    )


@public_router.post("/paystack/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str | None = Header(None, alias="x-paystack-signature"),
    db: Session = Depends(get_session),
):
    raw = await request.body()

    print("\n" + "=" * 80)
    print("PAYSTACK WEBHOOK RECEIVED")
    print("=" * 80)
    print(f"Headers: {dict(request.headers)}")
    print(f"Signature: {x_paystack_signature}")
    print(f"Body length: {len(raw)}")
    print(f"Body: {raw.decode('utf-8')}")
    print("=" * 80 + "\n")

    if not x_paystack_signature:
        print("ERROR: Missing signature header")
        raise HTTPException(status_code=400, detail="Missing Paystack signature")

    is_valid = service.verify_paystack_signature(raw, x_paystack_signature)
    print(f"Signature valid: {is_valid}\n")

    if not is_valid:
        print("ERROR: Signature verification FAILED - returning 403")
        raise HTTPException(status_code=403, detail="Invalid Paystack signature")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    result = service.handle_webhook(db, payload)
    return {"status": True, "detail": result.get("detail")}


@router.get("/deposit/{reference}/status", response_model=DepositStatusOut)
def deposit_status(
    reference: str,
    db: Session = Depends(get_session),
    identity=Depends(get_current_identity),
):
    if not _has_permission_identity(identity, "read") and not hasattr(
        identity, "email"
    ):
        raise HTTPException(status_code=403, detail="API key missing read permission")

    data = service.verify_deposit_status(db, reference)
    return DepositStatusOut(
        reference=data["reference"], status=data["status"], amount=data["amount"]
    )


@router.get("/balance", response_model=BalanceOut)
def balance(db: Session = Depends(get_session), identity=Depends(get_current_identity)):
    if not _has_permission_identity(identity, "read"):
        raise HTTPException(status_code=403, detail="API key missing read permission")
    user_id = _identity_to_user_id(identity)
    bal = service.get_balance_for_user(db, user_id)
    return BalanceOut(balance=bal)


@router.post("/transfer", response_model=SimpleOut)
def transfer(
    req: TransferRequest,
    db: Session = Depends(get_session),
    identity=Depends(get_current_identity),
):
    if not _has_permission_identity(identity, "transfer"):
        raise HTTPException(
            status_code=403, detail="API key missing transfer permission"
        )

    user_id = _identity_to_user_id(identity)
    sender_wallet = service.get_wallet_by_user(db, user_id)
    if not sender_wallet:
        raise HTTPException(status_code=404, detail="Sender wallet not found")

    recipient_wallet = service.get_wallet_by_number(db, req.wallet_number)
    if not recipient_wallet:
        raise HTTPException(status_code=404, detail="Recipient wallet not found")

    service.transfer(db, sender_wallet, recipient_wallet, req.amount)
    return SimpleOut(status="success", message="Transfer completed")


@router.get("/transactions", response_model=TransactionListOut)
def transactions(
    db: Session = Depends(get_session), identity=Depends(get_current_identity)
):
    if not _has_permission_identity(identity, "read"):
        raise HTTPException(status_code=403, detail="API key missing read permission")
    user_id = _identity_to_user_id(identity)
    txs = service.list_transactions_for_user(db, user_id)
    out_list = [
        {
            "type": t.transaction_type,
            "amount": float(t.amount),
            "status": t.transaction_status,
        }
        for t in txs
    ]
    return TransactionListOut(transactions=out_list)


@router.get("/wallet")
def get_my_wallet(
    db: Session = Depends(get_session),
    identity=Depends(get_current_identity),
):
    """Get the current user's wallet number (no parameters needed)"""

    if not _has_permission_identity(identity, "read"):
        raise HTTPException(status_code=403, detail="API key missing read permission")

    user_id = _identity_to_user_id(identity)

    wallet = service.get_wallet_by_user(db, user_id)

    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for user")

    return {"wallet_number": wallet.wallet_number, "user_id": str(wallet.walletuser_id)}
