"""故事圣经相关模型：人物关系。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class CharacterRelationship(UUIDMixin, TimestampMixin, Base):
    """两个人物之间的关系。"""

    __tablename__ = "character_relationships"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("novel_projects.id"), index=True
    )
    character_a_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id"), index=True
    )
    character_b_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id"), index=True
    )
    relation_type: Mapped[str] = mapped_column(
        String(40), default="other"
    )  # ally/rival/lover/family/mentor/conflict/secret/other
    description: Mapped[str] = mapped_column(Text, default="")
    timeline_info: Mapped[str] = mapped_column(
        Text, default=""
    )  # 关系的时间线背景
    status: Mapped[str] = mapped_column(
        String(40), default="active"
    )  # active | draft
