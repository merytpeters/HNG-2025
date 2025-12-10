from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Boolean,
)
from sqlalchemy.orm import declarative_base, relationship
from uuid import uuid4

Base = declarative_base()


class WalletUser(Base):
    __tablename__ = "walletusers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    google_sub = Column(String(255), unique=True, nullable=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)

    api_keys = relationship(
        "APIKey", back_populates="walletuser", cascade="all, delete-orphan"
    )
    wallets = relationship(
        "Wallet", back_populates="walletuser", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="walletuser", cascade="all, delete-orphan"
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False)
    walletuser_id = Column(String(36), ForeignKey("walletusers.id"), nullable=False)
    hashed_secret = Column(String(255), nullable=False)
    permissions = Column(JSON, default=list)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    revoked = Column(Boolean, default=False, nullable=False)

    walletuser = relationship("WalletUser", back_populates="api_keys")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    balance = Column(Float, nullable=False)
    wallet_number = Column(Integer, nullable=False)
    walletuser_id = Column(String(36), ForeignKey("walletusers.id"), nullable=False)

    walletuser = relationship("WalletUser", back_populates="wallets")
    transactions = relationship(
        "Transaction", back_populates="wallet", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    transaction_type = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    reference = Column(String(100), nullable=False)
    transaction_status = Column(String(50), nullable=False)
    authorization_url = Column(String(255), nullable=True)

    wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=False)
    walletuser_id = Column(String(36), ForeignKey("walletusers.id"), nullable=False)

    wallet = relationship("Wallet", back_populates="transactions")
    walletuser = relationship("WalletUser", back_populates="transactions")
