"""M1 knowledge bases, documents and vector chunks.

Revision ID: 0002_knowledge
Revises: 0001_enable_vector
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0002_knowledge"
down_revision = "0001_enable_vector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("knowledge_bases", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("name", sa.String(120), nullable=False, unique=True))
    op.create_table("documents", sa.Column("id", sa.String(36), primary_key=True),
                    sa.Column("knowledge_base_id", sa.Integer(), sa.ForeignKey("knowledge_bases.id"), nullable=False),
                    sa.Column("filename", sa.String(255), nullable=False), sa.Column("source_url", sa.Text()),
                    sa.Column("product", sa.String(120)), sa.Column("product_version", sa.String(80)),
                    sa.Column("sha256", sa.String(64), nullable=False), sa.Column("stored_path", sa.Text(), nullable=False),
                    sa.Column("status", sa.String(24), nullable=False), sa.Column("error", sa.Text()),
                    sa.Column("embedding_model", sa.String(120), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_documents_knowledge_base_id", "documents", ["knowledge_base_id"])
    op.create_table("chunks", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
                    sa.Column("ordinal", sa.Integer(), nullable=False), sa.Column("heading", sa.String(255)),
                    sa.Column("page", sa.Integer()), sa.Column("content", sa.Text(), nullable=False),
                    sa.Column("embedding", Vector(2560), nullable=False))
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("knowledge_bases")
