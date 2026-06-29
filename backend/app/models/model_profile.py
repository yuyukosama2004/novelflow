"""模型配置：存储用户配置的 AI provider 和模型选择。

API Key 存储在此表中。数据库文件已通过 .gitignore 排除（*.db / *.sqlite），
不会提交到 Git。前端查询时只返回 api_key_configured (bool)，不返回实际密钥值。
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModelProfile(UUIDMixin, TimestampMixin, Base):
    """用户配置的模型连接信息。"""

    __tablename__ = "model_profiles"

    name: Mapped[str] = mapped_column(String(100), default="")  # 显示名
    provider: Mapped[str] = mapped_column(
        String(40), default="deepseek"
    )  # deepseek | ollama | openai_compatible
    base_url: Mapped[str] = mapped_column(String(300), default="")
    api_key: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[str] = mapped_column(
        String(100), default=""
    )  # 默认模型名
    extra_models_json: Mapped[list[str]] = mapped_column(
        String, default="[]"
    )  # JSON 编码的额外可选模型列表（兼容 SQLite 无原生 JSON 类型）
    temperature: Mapped[float] = mapped_column(default=0.7)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
