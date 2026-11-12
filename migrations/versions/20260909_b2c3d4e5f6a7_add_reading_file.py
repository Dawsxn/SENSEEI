"""add reading file

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-09

The instructor's original upload, kept now that the student reads it on screen
rather than reading the extracted text. A separate table, not a column on
`reading`: the reading list selects whole reading rows, and a blob there would
be fetched by every request that only wanted a title.

Existing readings have no row here and fall back to the text view, which is also
the state every reading stays in until the upload flow exists.
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reading_file",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("media_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reading_id"], ["reading.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Unique rather than a plain index: one file per reading is a rule, so the
    # database holds it instead of the code that happens to write the row.
    op.create_index(
        "ix_reading_file_reading_id", "reading_file", ["reading_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_reading_file_reading_id", table_name="reading_file")
    op.drop_table("reading_file")
