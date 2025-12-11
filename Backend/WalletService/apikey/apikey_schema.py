from datetime import datetime, timezone
from pydantic import BaseModel
from WalletService.user.enums import APIKey_Permissions
from typing import List, Optional


class APIKeyCreateSchema(BaseModel):
    walletuser_id: str
    secret: str
    name: str
    permissions: List[APIKey_Permissions]
    expires_at: datetime
    created_at: datetime = datetime.now(timezone.utc)
    revoked: bool = False


class PermissionOut(BaseModel):
    type: str


class APIKeyOut(BaseModel):
    walletuser_id: str
    name: str
    secret: Optional[str]
    permissions: List[PermissionOut]
    expires_at: datetime
    created_at: datetime
    revoked: bool


class APIKeyCreateRequest(BaseModel):
    name: str
    permissions: List[str]
    expiry: str


class RolloverAPIKeyRequest(BaseModel):
    expired_key_id: str
    expiry: str
