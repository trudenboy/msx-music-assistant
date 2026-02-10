"""Pydantic models for MSX JSON API."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MsxTemplateType(str, Enum):
    """MSX Template types."""

    SEPARATE = "separate"
    LIST = "list"


class MsxTemplate(BaseModel):
    """MSX Template model."""

    model_config = ConfigDict(populate_by_name=True)

    type: MsxTemplateType | str = MsxTemplateType.SEPARATE
    layout: str | None = None
    icon: str | None = None
    action: str | None = None
    image_filler: str | None = Field(None, alias="imageFiller")


class MsxItem(BaseModel):
    """MSX Content Item model."""

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    label: str | None = None
    image: str | None = None
    icon: str | None = None
    action: str | None = None
    background: str | None = None
    player_label: str | None = Field(None, alias="playerLabel")
    title_footer: str | None = Field(None, alias="titleFooter")
    content: str | None = None


class MsxContent(BaseModel):
    """MSX Content Page model."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = "list"
    headline: str | None = None
    template: MsxTemplate | None = None
    items: list[MsxItem] | None = None
    action: str | None = None
    hint: str | None = None
