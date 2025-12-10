from pydantic import BaseModel, Field
from typing import Optional, List


class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0)


class DepositInitOut(BaseModel):
    reference: str
    authorization_url: str


class DepositStatusOut(BaseModel):
    reference: str
    status: str
    amount: float


class TransferRequest(BaseModel):
    wallet_number: int
    amount: float = Field(..., gt=0)


class SimpleOut(BaseModel):
    status: str
    message: str


class BalanceOut(BaseModel):
    balance: float


class TransactionOut(BaseModel):
    type: str
    amount: float
    status: str


class TransactionListOut(BaseModel):
    transactions: List[TransactionOut]
