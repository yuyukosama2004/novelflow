from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DDL,
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, utc_now


class CanonCommit(UUIDMixin, Base):
    """Immutable record of one scene version entering the official manuscript."""

    __tablename__ = "canon_commits"
    __table_args__ = (
        UniqueConstraint("scene_id", "sequence_no", name="uq_canon_commit_scene_sequence"),
        UniqueConstraint("scene_version_id", name="uq_canon_commit_scene_version"),
        CheckConstraint("sequence_no > 0", name="ck_canon_commit_positive_sequence"),
        CheckConstraint("length(content_hash) = 64", name="ck_canon_commit_hash_length"),
    )

    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id"), index=True)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"), index=True)
    scene_version_id: Mapped[str] = mapped_column(ForeignKey("scene_versions.id"), index=True)
    previous_commit_id: Mapped[str | None] = mapped_column(
        ForeignKey("canon_commits.id"),
        nullable=True,
        index=True,
    )
    sequence_no: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    contract_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    review_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    commit_reason: Mapped[str] = mapped_column(String(40))
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    committed_by: Mapped[str] = mapped_column(String(80), default="user")
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


event.listen(
    CanonCommit.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER canon_commits_prevent_update
        BEFORE UPDATE ON canon_commits
        BEGIN
            SELECT RAISE(ABORT, 'canon commits are immutable');
        END
        """
    ).execute_if(dialect="sqlite"),
)
event.listen(
    CanonCommit.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER canon_commits_prevent_delete
        BEFORE DELETE ON canon_commits
        BEGIN
            SELECT RAISE(ABORT, 'canon commits are immutable');
        END
        """
    ).execute_if(dialect="sqlite"),
)
event.listen(
    CanonCommit.__table__,
    "before_drop",
    DDL("DROP TRIGGER IF EXISTS canon_commits_prevent_update").execute_if(dialect="sqlite"),
)
event.listen(
    CanonCommit.__table__,
    "before_drop",
    DDL("DROP TRIGGER IF EXISTS canon_commits_prevent_delete").execute_if(dialect="sqlite"),
)
