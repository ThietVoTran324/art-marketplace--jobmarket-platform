"""Admin FAQ CMS routes (AI_RAG_FAQ_CMS)."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from app.api.rest.dependencies import db, require_roles
from app.postgresql.models import FaqArticlesOrm

router = APIRouter(tags=["admin-faq"])

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class FaqArticleIn(BaseModel):
    slug: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1)
    status: str = Field(default="draft")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if not _SLUG_RE.match(s):
            raise ValueError("slug must be lowercase kebab-case (a-z0-9-)")
        return s

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if s not in {"draft", "published"}:
            raise ValueError("status must be draft or published")
        return s


class FaqArticlePatch(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    body: str | None = Field(default=None, min_length=1)
    status: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        if v is None:
            return v
        s = v.strip().lower()
        if not _SLUG_RE.match(s):
            raise ValueError("slug must be lowercase kebab-case (a-z0-9-)")
        return s

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        s = v.strip().lower()
        if s not in {"draft", "published"}:
            raise ValueError("status must be draft or published")
        return s


class FaqArticleOut(BaseModel):
    id: int
    slug: str
    title: str
    body: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReindexQueuedOut(BaseModel):
    queued: bool
    task: str
    slug: str | None = None


def _enqueue_reindex_slug(slug: str) -> None:
    from app.ai.tasks import reindex_faq_article_task

    reindex_faq_article_task.delay(slug)


def _enqueue_reindex_all_faq() -> None:
    from app.ai.tasks import reindex_rag_corpus

    reindex_rag_corpus.delay("faq")


@router.get("/faq", response_model=list[FaqArticleOut])
async def list_faq_articles(
    db: db,
    _: int = Depends(require_roles("admin")),
):
    rows = (
        await db.scalars(select(FaqArticlesOrm).order_by(FaqArticlesOrm.id.asc()))
    ).all()
    return list(rows)


@router.post("/faq", response_model=FaqArticleOut, status_code=status.HTTP_201_CREATED)
async def create_faq_article(
    body: FaqArticleIn,
    db: db,
    _: int = Depends(require_roles("admin")),
):
    exists = await db.scalar(
        select(FaqArticlesOrm.id).where(FaqArticlesOrm.slug == body.slug)
    )
    if exists is not None:
        raise HTTPException(status_code=400, detail="slug already exists")
    row = FaqArticlesOrm(
        slug=body.slug,
        title=body.title.strip(),
        body=body.body,
        status=body.status,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    if row.status == "published":
        _enqueue_reindex_slug(row.slug)
    return row


@router.post("/faq/reindex-all", response_model=ReindexQueuedOut)
async def reindex_all_faq(
    _: int = Depends(require_roles("admin")),
):
    _enqueue_reindex_all_faq()
    return ReindexQueuedOut(queued=True, task="reindex_rag_corpus", slug=None)


@router.get("/faq/{article_id}", response_model=FaqArticleOut)
async def get_faq_article(
    article_id: int,
    db: db,
    _: int = Depends(require_roles("admin")),
):
    row = await db.scalar(select(FaqArticlesOrm).where(FaqArticlesOrm.id == article_id))
    if row is None:
        raise HTTPException(status_code=404, detail="faq not found")
    return row


@router.patch("/faq/{article_id}", response_model=FaqArticleOut)
async def patch_faq_article(
    article_id: int,
    body: FaqArticlePatch,
    db: db,
    _: int = Depends(require_roles("admin")),
):
    row = await db.scalar(select(FaqArticlesOrm).where(FaqArticlesOrm.id == article_id))
    if row is None:
        raise HTTPException(status_code=404, detail="faq not found")

    old_slug = row.slug
    old_status = row.status
    data = body.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] != row.slug:
        clash = await db.scalar(
            select(FaqArticlesOrm.id).where(
                FaqArticlesOrm.slug == data["slug"],
                FaqArticlesOrm.id != article_id,
            )
        )
        if clash is not None:
            raise HTTPException(status_code=400, detail="slug already exists")
        row.slug = data["slug"]
    if "title" in data:
        row.title = data["title"].strip()
    if "body" in data:
        row.body = data["body"]
    if "status" in data:
        row.status = data["status"]
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)

    # Reindex new slug; if slug changed or unpublished, drop old index key.
    if old_slug != row.slug:
        _enqueue_reindex_slug(old_slug)
    if row.status == "published" or old_status == "published":
        _enqueue_reindex_slug(row.slug)
    return row


@router.post("/faq/{article_id}/reindex", response_model=ReindexQueuedOut)
async def reindex_one_faq(
    article_id: int,
    db: db,
    _: int = Depends(require_roles("admin")),
):
    row = await db.scalar(select(FaqArticlesOrm).where(FaqArticlesOrm.id == article_id))
    if row is None:
        raise HTTPException(status_code=404, detail="faq not found")
    _enqueue_reindex_slug(row.slug)
    return ReindexQueuedOut(queued=True, task="reindex_faq_article", slug=row.slug)
