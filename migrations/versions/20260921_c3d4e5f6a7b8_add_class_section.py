"""add class section

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-21

A class's section moves out of its name into its own column, so `STRAMA - K31`
becomes name `STRAMA`, section `K31`. Existing rows written as `NAME - SECTION`
are split on the way through; anything else keeps its name and gets an empty
section rather than a guess.

Also adds the rule that one instructor cannot hold the same course and section
twice, ignoring case.
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "class",
        sa.Column("section", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.execute(
        """
        UPDATE class
        SET section = trim(split_part(name, ' - ', 2)),
            name    = trim(split_part(name, ' - ', 1))
        WHERE position(' - ' in name) > 0
        """
    )
    op.execute("UPDATE class SET section = '' WHERE section IS NULL")
    op.alter_column("class", "section", nullable=False)

    op.create_index(
        "uq_class_name_section",
        "class",
        ["instructor_id", sa.text("lower(name)"), sa.text("lower(section)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_class_name_section", table_name="class")
    op.execute(
        "UPDATE class SET name = name || ' - ' || section WHERE section <> ''"
    )
    op.drop_column("class", "section")
