"""add reading description

Revision ID: a1b2c3d4e5f6
Revises: 8f3c1a2b4d5e
Create Date: 2026-09-04

A short one-line topic summary shown under the title in the reading list.
Nullable, so existing readings are unaffected; the upload screen will set it once
that exists.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "8f3c1a2b4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reading",
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reading", "description")
