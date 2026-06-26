from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ResellerStatus(StrEnum):
    pending = 'pending'
    active = 'active'
    limited = 'limited'
    disabled = 'disabled'


class WalletTransactionType(StrEnum):
    manual_credit = 'manual_credit'
    manual_debit = 'manual_debit'
    payment_credit = 'payment_credit'
    usage_charge = 'usage_charge'
    correction = 'correction'


class Reseller(Base):
    __tablename__ = 'resellers'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pasar_admin_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    pasar_username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    pasar_role_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default=ResellerStatus.pending.value, index=True)
    balance_toman: Mapped[int] = mapped_column(BigInteger, default=0)
    price_per_gb_toman: Mapped[int] = mapped_column(Integer, default=5000)
    debt_limit_toman: Mapped[int] = mapped_column(Integer, default=50000)
    last_total_usage_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    low_balance_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    wallet_transactions: Mapped[list['WalletTransaction']] = relationship(back_populates='reseller')
    usage_snapshots: Mapped[list['UsageSnapshot']] = relationship(back_populates='reseller')


class WalletTransaction(Base):
    __tablename__ = 'wallet_transactions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reseller_id: Mapped[int] = mapped_column(ForeignKey('resellers.id'), index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    amount_toman: Mapped[int] = mapped_column(BigInteger)
    balance_before_toman: Mapped[int] = mapped_column(BigInteger)
    balance_after_toman: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reseller: Mapped[Reseller] = relationship(back_populates='wallet_transactions')


class UsageSnapshot(Base):
    __tablename__ = 'usage_snapshots'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reseller_id: Mapped[int] = mapped_column(ForeignKey('resellers.id'), index=True)
    old_usage_bytes: Mapped[int] = mapped_column(BigInteger)
    total_usage_bytes: Mapped[int] = mapped_column(BigInteger)
    delta_usage_bytes: Mapped[int] = mapped_column(BigInteger)
    cost_toman: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reseller: Mapped[Reseller] = relationship(back_populates='usage_snapshots')
