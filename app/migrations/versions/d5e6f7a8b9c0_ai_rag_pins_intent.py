"""AI RAG 1.1: chunk_kind + ai_rag_tag_embeddings.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-11-06 09:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EMBED_DIMS = 768


def upgrade() -> None:
    # Idempotent: local may already have columns/tables from create_all / partial runs.
    op.execute(
        """
        ALTER TABLE ai_rag_chunks
        ADD COLUMN IF NOT EXISTS chunk_kind VARCHAR(40)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ai_rag_chunks_chunk_kind
        ON ai_rag_chunks (chunk_kind)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_rag_tag_embeddings (
            tag_id INTEGER PRIMARY KEY REFERENCES tags(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            meta JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        f"""
        ALTER TABLE ai_rag_tag_embeddings
        ADD COLUMN IF NOT EXISTS embedding vector({_EMBED_DIMS})
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ai_rag_tag_embeddings_name
        ON ai_rag_tag_embeddings (name)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ai_rag_tag_embeddings_name")
    op.execute("DROP TABLE IF EXISTS ai_rag_tag_embeddings")
    op.execute("DROP INDEX IF EXISTS ix_ai_rag_chunks_chunk_kind")
    op.execute("ALTER TABLE ai_rag_chunks DROP COLUMN IF EXISTS chunk_kind")
