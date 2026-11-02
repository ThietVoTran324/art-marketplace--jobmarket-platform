"""Pydantic schemas for Gemini structured JSON output."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ImageTagSuggestion(BaseModel):
    """One category/tag label proposed by the vision model."""

    name: str = Field(..., min_length=1, max_length=100)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("empty tag name")
        return cleaned


class ImageTagResult(BaseModel):
    """Root JSON shape returned by Gemini for auto-tag."""

    tags: list[ImageTagSuggestion] = Field(default_factory=list, max_length=16)

    @field_validator("tags")
    @classmethod
    def drop_blank(cls, value: list[ImageTagSuggestion]) -> list[ImageTagSuggestion]:
        return [t for t in value if t.name.strip()]
