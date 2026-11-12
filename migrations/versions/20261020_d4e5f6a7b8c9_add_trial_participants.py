"""add trial participants

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-20

What trial mode needs (docs/context/trial.md): a mode on each class, and the
participant IDs, made in batches, that sign in as students. Existing classes
are all SEE-I classes, which is the column's default.

The session gains a `timed_out` status, but status is stored as text, so that
needs no change here.
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "class",
        sa.Column("mode", sa.String(length=16), server_default="seei", nullable=False),
    )

    op.create_table(
        "participant_batch",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instructor_id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["instructor_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_participant_batch_instructor_id"),
        "participant_batch",
        ["instructor_id"],
    )

    op.create_table(
        "participant",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("class_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("signed_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clock_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["participant_batch.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["class_id"], ["class.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_participant_batch_id"), "participant", ["batch_id"])
    op.create_index(op.f("ix_participant_user_id"), "participant", ["user_id"], unique=True)
    op.create_index(op.f("ix_participant_class_id"), "participant", ["class_id"])
    op.create_index("uq_participant_code", "participant", ["code"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_participant_code", table_name="participant")
    op.drop_index(op.f("ix_participant_class_id"), table_name="participant")
    op.drop_index(op.f("ix_participant_user_id"), table_name="participant")
    op.drop_index(op.f("ix_participant_batch_id"), table_name="participant")
    op.drop_table("participant")
    op.drop_index(op.f("ix_participant_batch_instructor_id"), table_name="participant_batch")
    op.drop_table("participant_batch")
    op.drop_column("class", "mode")
