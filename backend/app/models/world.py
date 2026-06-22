from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorldEntry(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "world_entries"

    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id"), index=True)
    entry_type: Mapped[str] = mapped_column(String(40), default="custom")
    name: Mapped[str] = mapped_column(String(180))
    summary: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    canon_status: Mapped[str] = mapped_column(String(40), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)

    project = relationship("NovelProject", back_populates="world_entries")
