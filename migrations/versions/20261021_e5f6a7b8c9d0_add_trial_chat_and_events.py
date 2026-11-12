"""add trial chat and events

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-21

The control groups and the event log (docs/context/trial.md): when a
participant pressed Done, the chatbot group's messages, and one row per
recorded interaction.
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "participant", sa.Column("done_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        "chat_message",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_message_participant_id"), "chat_message", ["participant_id"])

    op.create_table(
        "trial_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trial_event_participant_id"), "trial_event", ["participant_id"])
    op.create_index("ix_trial_event_participant_at", "trial_event", ["participant_id", "at"])


def downgrade() -> None:
    op.drop_index("ix_trial_event_participant_at", table_name="trial_event")
    op.drop_index(op.f("ix_trial_event_participant_id"), table_name="trial_event")
    op.drop_table("trial_event")
    op.drop_index(op.f("ix_chat_message_participant_id"), table_name="chat_message")
    op.drop_table("chat_message")
    op.drop_column("participant", "done_at")
