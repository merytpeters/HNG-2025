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

service = WalletService()


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


@router.post("/paystack/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(..., alias="x-paystack-signature"),
    db: Session = Depends(get_session),
):
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature") or request.headers.get(
        "X-Paystack-Signature"
    )
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Paystack signature")

    if not service.verify_paystack_signature(raw, signature):
        raise HTTPException(status_code=403, detail="Invalid Paystack signature")

    payload = await request.json()
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
