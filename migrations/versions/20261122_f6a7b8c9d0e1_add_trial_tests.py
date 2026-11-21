"""add trial tests

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-22

The pre-test and post-test taken in the trial app (docs/context/trial.md): which
test a class takes, when each participant's tests started and how they ended,
and one row per answer.

The grader role needs no change here: roles are stored as text.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STAGES = ("pretest", "posttest")


def upgrade() -> None:
    op.add_column("class", sa.Column("test_key", sa.String(length=64), nullable=True))

    for stage in STAGES:
        op.add_column(
            "participant", sa.Column(f"{stage}_started_at", sa.DateTime(timezone=True), nullable=True)
        )
        op.add_column(
            "participant", sa.Column(f"{stage}_ended_at", sa.DateTime(timezone=True), nullable=True)
        )
        op.add_column(
            "participant", sa.Column(f"{stage}_ended_by", sa.String(length=16), nullable=True)
        )

    op.create_table(
        "test_answer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("test", sa.String(length=8), nullable=False),
        sa.Column("item", sa.String(length=16), nullable=False),
        sa.Column("choice", sa.String(length=4), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("groups", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sure", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("edits", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_answer_participant_id"), "test_answer", ["participant_id"])
    op.create_index(
        "uq_test_answer_item", "test_answer", ["participant_id", "test", "item"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_test_answer_item", table_name="test_answer")
    op.drop_index(op.f("ix_test_answer_participant_id"), table_name="test_answer")
    op.drop_table("test_answer")
    for stage in reversed(STAGES):
        for col in ("ended_by", "ended_at", "started_at"):
            op.drop_column("participant", f"{stage}_{col}")
    op.drop_column("class", "test_key")
