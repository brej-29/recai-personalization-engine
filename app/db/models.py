from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    CheckConstraint,
    Date,
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
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON, "sqlite"),
        nullable=True,
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


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB().with_variant(JSON, "sqlite"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )

    assignments: Mapped[List["Assignment"]] = relationship(back_populates="experiment")
    events: Mapped[List["EventsAgg"]] = relationship(back_populates="experiment")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    variant: Mapped[str] = mapped_column(String(64), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, nullable=False
    )

    experiment: Mapped["Experiment"] = relationship(back_populates="assignments")

    __table_args__ = (
        UniqueConstraint("user_id", "experiment_id", name="uq_assignments_user_experiment"),
    )


class EventsAgg(Base):
    __tablename__ = "events_agg"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    variant: Mapped[str] = mapped_column(String(64), nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    experiment: Mapped["Experiment"] = relationship(back_populates="events")

    __table_args__ = (
        UniqueConstraint("date", "experiment_id", "variant", name="uq_eventsagg_date_experiment_variant"),
    )