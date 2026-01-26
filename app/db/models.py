from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), nullable=True
    )

    interactions: Mapped[List["Interaction"]] = relationship(back_populates="user")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    genres: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), nullable=True
    )

    interactions: Mapped[List["Interaction"]] = relationship(back_populates="item")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    rating: Mapped[Optional[float]] = mapped_column(nullable=True)
    ts: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="interactions")
    item: Mapped["Item"] = relationship(back_populates="interactions")

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('view', 'click', 'rate')",
            name="ck_interactions_event_type",
        ),
        Index("ix_interactions_user_ts", "user_id", "ts"),
        Index("ix_interactions_item_ts", "item_id", "ts"),
        Index("ix_interactions_user_item", "user_id", "item_id"),
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), nullable=True
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __table_args__ = (UniqueConstraint("name", "version", name="uq_model_versions_name_version"),)