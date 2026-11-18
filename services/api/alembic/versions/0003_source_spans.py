"""Add stable source text spans to chunks.

Revision ID: 0003_source_spans
Revises: 0002_knowledge
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_source_spans"
down_revision = "0002_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("source_start", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("source_end", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "source_end")
    op.drop_column("chunks", "source_start")
