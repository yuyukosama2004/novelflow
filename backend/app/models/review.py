from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ReviewIssue(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "review_issues"

    scene_version_id: Mapped[str] = mapped_column(ForeignKey("scene_versions.id"), index=True)
    issue_type: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20))
    evidence_json: Mapped[str] = mapped_column(Text, default="")
    conflict_rule: Mapped[str] = mapped_column(Text, default="")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(
        String(40), default="open"
    )  # open | accepted | ignored | false_positive

    scene_version = relationship("SceneVersion", back_populates="review_issues")
