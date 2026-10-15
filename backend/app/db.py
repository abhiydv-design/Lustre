"""Database models (SQLAlchemy 2.0). SQLite for the MVP; Postgres works unchanged."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


def _id() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(120))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CreditEntry(Base):
    """Append-only ledger. `ref` is unique, which makes every charge, refund and top-up idempotent."""
    __tablename__ = "credit_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(40))
    ref: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Shoot(Base):
    __tablename__ = "shoots"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    jewellery_type: Mapped[str] = mapped_column(String(30))
    metal: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    photos: Mapped[list["SourcePhoto"]] = relationship(back_populates="shoot", order_by="SourcePhoto.position")


class SourcePhoto(Base):
    __tablename__ = "source_photos"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    shoot_id: Mapped[str] = mapped_column(ForeignKey("shoots.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    original_key: Mapped[str] = mapped_column(String(255))
    product_key: Mapped[str | None] = mapped_column(String(255), nullable=True)  # prepared cut-out PNG
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    shoot: Mapped[Shoot] = relationship(back_populates="photos")


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    shoot_id: Mapped[str] = mapped_column(ForeignKey("shoots.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    style: Mapped[str] = mapped_column(String(30))
    fmt: Mapped[str] = mapped_column(String(10))
    count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|done|failed
    stage: Mapped[str] = mapped_column(String(20), default="queued")   # cutout|scene|lighting|ready
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    variations: Mapped[list["Variation"]] = relationship(back_populates="job", order_by="Variation.position")


class Variation(Base):
    __tablename__ = "variations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    photo_id: Mapped[str] = mapped_column(ForeignKey("source_photos.id"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    seed: Mapped[int] = mapped_column(Integer)
    scene_key: Mapped[str] = mapped_column(String(255))      # generated background at preview size
    preview_key: Mapped[str] = mapped_column(String(255))
    preview_fidelity: Mapped[float] = mapped_column(Float, default=0.0)
    final_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    final_status: Mapped[str] = mapped_column(String(20), default="none")  # none|rendering|ready|failed
    final_fidelity: Mapped[float | None] = mapped_column(Float, nullable=True)
    render_attempts: Mapped[int] = mapped_column(Integer, default=0)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    job: Mapped[Job] = relationship(back_populates="variations")


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    pack: Mapped[str] = mapped_column(String(20))
    credits: Mapped[int] = mapped_column(Integer)
    amount_paise: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="created")  # created|paid
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


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
