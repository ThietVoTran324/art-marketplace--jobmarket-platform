"""PinOut helpers — never expose original_image path on public API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class PinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str | None = None
    description: str | None = None
    href: str | None = None
    image: str | None = None
    rgb: str | None = None
    height: str | None = None
    created_at: datetime | None = None
    videoPreview: str | None = None
    has_original: bool = False

    @model_validator(mode="before")
    @classmethod
    def _map_orm_strip_original_path(cls, data: Any) -> Any:
        if isinstance(data, dict):
            path = data.pop("original_image", None)
            if "has_original" not in data:
                data["has_original"] = bool(path)
            return data
        return {
            "id": data.id,
            "user_id": data.user_id,
            "title": data.title,
            "description": data.description,
            "href": data.href,
            "image": data.image,
            "rgb": data.rgb,
            "height": data.height,
            "created_at": data.created_at,
            "videoPreview": data.videoPreview,
            "has_original": bool(getattr(data, "original_image", None)),
        }


class PinIn(BaseModel):
    title: str | None = None
    description: str | None = None
    href: str | None = None
    height: str | None = None


class OriginalUrlOut(BaseModel):
    url: str
    expires_in: int


class FilterParams(BaseModel):
    offset: int = 0
    limit: int = 10


class FilterWithValue(FilterParams):
    value: str


class FeedMetaIn(BaseModel):
    pin_ids: list[int]


class FeedMetaOut(BaseModel):
    pin_id: int
    username: str | None = None
    likes_count: int = 0
    liked: bool = False
    comments_count: int = 0


class PinEngagementOut(BaseModel):
    pin_id: int
    likes_count: int = 0
    saves_count: int = 0
    views_count: int = 0
