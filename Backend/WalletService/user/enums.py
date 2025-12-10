from enum import Enum


class APIKey_Permissions(Enum):
    DEPOSIT = "deposit"
    READ = "read"
    TRANSFER = "transfer"


class TransactionStatus(Enum):
    FAILED = "failed"
    PENDING = "pending"
    SUCCESS = "success"


class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
