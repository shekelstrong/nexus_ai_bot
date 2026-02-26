from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional


from sqlalchemy import (
    BigInteger,
    String,
    Integer,
    DateTime,
    Numeric,
    ForeignKey,
    Index,
    Text,
    Boolean,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class SubscriptionTier(str, PyEnum):
    FREE = "FREE"
    PREMIUM = "PREMIUM"
    PREMIUM_X2 = "PREMIUM_X2"


class GenerationCategory(str, PyEnum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    SEARCH = "SEARCH"  # Добавили SEARCH


class GenerationStatus(str, PyEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TransactionType(str, PyEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    REF_REWARD = "REF_REWARD"
    SUBSCRIPTION = "SUBSCRIPTION"
    TOKEN_PURCHASE = "TOKEN_PURCHASE"


class TransactionStatus(str, PyEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))

    referral_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    referrer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )

    tokens_balance: Mapped[int] = mapped_column(Integer, default=10)
    referral_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    subscription_tier: Mapped[str] = mapped_column(String(32), default=SubscriptionTier.FREE.value)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    daily_tokens_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow() + timedelta(days=1),
    )

    language_code: Mapped[str] = mapped_column(String(10), default="ru")
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)

    api_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    
    # Поле для хранения текущей активной модели (режим диалога)
    current_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    referrer: Mapped[Optional["User"]] = relationship(
        "User", remote_side=[id], foreign_keys=[referrer_id]
    )
    generations: Mapped[list["Generation"]] = relationship(
        "Generation", back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    templates: Mapped[list["Template"]] = relationship(
        "Template", back_populates="user", cascade="all, delete-orphan"
    )
    # История сообщений
    messages: Mapped[list["MessageHistory"]] = relationship(
        "MessageHistory", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_users_telegram_id", "telegram_id"),
        Index("idx_users_referral_code", "referral_code"),
        Index("idx_users_referrer_id", "referrer_id"),
        Index("idx_users_subscription_tier", "subscription_tier"),
        Index("idx_users_created_at", "created_at"),
    )


class MessageHistory(Base):
    """Таблица для хранения истории переписки с моделями"""
    __tablename__ = "message_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)     # Текст сообщения
    model_id: Mapped[str] = mapped_column(String(100), nullable=False) # С какой моделью общались
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    user: Mapped["User"] = relationship("User", back_populates="messages")
    
    __table_args__ = (
        Index("idx_history_user_model", "user_id", "model_id"),
    )


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=GenerationStatus.PENDING.value)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    cost: Mapped[int] = mapped_column(Integer, default=1)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="generations")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=TransactionStatus.PENDING.value)
    
    payment_system: Mapped[str] = mapped_column(String(50))
    payment_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship("User", back_populates="transactions")


class ReferralStats(Base):
    __tablename__ = "referral_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    referral_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="templates")


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(20))
    module: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromoCode(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    tokens: Mapped[int] = mapped_column(Integer)
    activations_left: Mapped[int] = mapped_column(Integer, default=1)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))