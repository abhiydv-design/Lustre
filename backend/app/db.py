"""Database models (SQLAlchemy 2.0). SQLite for the MVP; Postgres works unchanged."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


def _id() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    """A guest until `phone` is set by OTP sign-in."""
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    @property
    def is_guest(self) -> bool:
        return self.phone is None


class OtpCode(Base):
    __tablename__ = "otp_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CreditEntry(Base):
    """Append-only ledger. `ref` is unique, which makes every charge, refund and top-up idempotent."""
    __tablename__ = "credit_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(40))
    ref: Mapped[str] = mapped_column(String(120), unique=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Product(Base):
    """A catalogue product (spec §9.3). Name and category are required; the rest is optional."""
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(20))
    sku: Mapped[str | None] = mapped_column(String(60), nullable=True)
    metal: Mapped[str | None] = mapped_column(String(30), nullable=True)
    metal_source: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "user" | "detected"
    stone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    collection: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    photos: Mapped[list["SourcePhoto"]] = relationship(back_populates="product", order_by="SourcePhoto.position")


class SourcePhoto(Base):
    __tablename__ = "source_photos"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    original_key: Mapped[str] = mapped_column(String(255))
    product_key: Mapped[str | None] = mapped_column(String(255), nullable=True)  # prepared cut-out PNG
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    hints: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    product: Mapped[Product] = relationship(back_populates="photos")


class Generation(Base):
    """One generated image (spec §9.4). Charged when requested; refunded automatically if it fails."""
    __tablename__ = "generations"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    photo_id: Mapped[str | None] = mapped_column(String(32), nullable=True)  # None once the source photo is deleted
    output: Mapped[str] = mapped_column(String(20))                # catalogue | marketplace
    preset: Mapped[str] = mapped_column(String(30))
    aspect: Mapped[str] = mapped_column(String(10))
    marketplace_preset: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cost: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|done|failed
    stage: Mapped[str] = mapped_column(String(20), default="queued")   # cutout|scene|lighting|upscale|ready
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    seed: Mapped[int] = mapped_column(Integer, default=0)
    scene_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    final_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fidelity: Mapped[float | None] = mapped_column(Float, nullable=True)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    review: Mapped[str] = mapped_column(String(20), default="pending")  # pending|accepted|reported
    provider_cost_inr: Mapped[float] = mapped_column(Float, default=0.0)  # estimate, for cost per image (§16.3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Report(Base):
    """A user's quality report (spec §9.5), kept for quality analysis (§16.2)."""
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    generation_id: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(20))         # product_detail | visual_quality
    category: Mapped[str] = mapped_column(String(40))
    note: Mapped[str] = mapped_column(Text, default="")
    refund: Mapped[str] = mapped_column(String(20))       # refunded|under_review|declined|not_eligible|duplicate
    # Snapshot for analysis that survives image deletion
    product_category: Mapped[str] = mapped_column(String(20), default="")
    preset: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # Set when a person on the team resolves an under_review report
    resolved_by: Mapped[str | None] = mapped_column(String(60), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_message: Mapped[str | None] = mapped_column(Text, nullable=True)     # shown to the jeweller
    internal_note: Mapped[str | None] = mapped_column(Text, nullable=True)    # team only


class Event(Base):
    """Things the database can't otherwise tell us, for usage metrics (§16.1): downloads and shares."""
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    generation_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    type: Mapped[str] = mapped_column(String(20))         # download | share
    channel: Mapped[str | None] = mapped_column(String(30), nullable=True)  # whatsapp, instagram, other
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class AdminAudit(Base):
    """Every team action and every look at a customer image (§14: limited, governed support access)."""
    __tablename__ = "admin_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin: Mapped[str] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(40))       # view_image | resolve_report | view_queue | view_metrics
    target: Mapped[str] = mapped_column(String(80), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    order_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    pack: Mapped[str] = mapped_column(String(20))
    credits: Mapped[int] = mapped_column(Integer)
    amount_paise: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="created")  # created|paid
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


SessionLocal: sessionmaker | None = None


def init_db(url: str) -> None:
    global SessionLocal
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(engine, expire_on_commit=False)


def new_session():
    assert SessionLocal is not None, "init_db() has not been called"
    return SessionLocal()
