from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .apikey_service import APIKeyService
from .apikey_schema import APIKeyCreateRequest, RolloverAPIKeyRequest
from WalletService.auth.jwt import get_current_identity
from db import get_session
from WalletService.user.models import WalletUser

router = APIRouter(prefix="/keys", tags=["API Keys"])
apikey_service = APIKeyService()


@router.post("/create", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: APIKeyCreateRequest,
    db: Session = Depends(get_session),
    current_user: WalletUser = Depends(get_current_identity),
):
    """
    Create a new API key for the authenticated user.
    """
    if not payload.permissions:
        raise HTTPException(status_code=400, detail="Permissions must be provided")

    result = apikey_service.create_key_with_expiry(
        db=db,
        user_id=current_user.id,
        name=payload.name,
        permissions=payload.permissions,
        expiry=payload.expiry,
    )
    return result


@router.post("/rollover", response_model=dict, status_code=status.HTTP_201_CREATED)
def rollover_api_key(
    payload: RolloverAPIKeyRequest,
    db: Session = Depends(get_session),
    current_user: WalletUser = Depends(get_current_identity),
):
    """
    Roll over an expired API key: create a new key using the same permissions.
    """
    old_key = apikey_service.get_api_key(db, payload.expired_key_id)
    if old_key is None:
        raise HTTPException(status_code=404, detail="Expired key not found")

    if hasattr(old_key, "first") and callable(getattr(old_key, "first")):
        old_key = old_key.first()

    if not old_key:
        raise HTTPException(status_code=404, detail="Expired key not found")

    owner_id = getattr(old_key, "walletuser_id", None)
    if owner_id is None:
        owner_id = getattr(old_key, "wallet_user_id", None) or getattr(
            old_key, "user_id", None
        )

    if owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to rollover this key")

    result = apikey_service.rollover_key(
        db=db,
        expired_key_id=payload.expired_key_id,
        expiry=payload.expiry,
    )
    return result
