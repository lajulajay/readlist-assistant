"""rename_podcast_episode_to_episode_id

Revision ID: 239ce4354440
Revises: 634e2df60ec1
Create Date: 2025-06-26 20:24:30.466496

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '239ce4354440'
down_revision = '634e2df60ec1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename podcast_episode column to episode_id
    op.alter_column('books', 'podcast_episode', new_column_name='episode_id')


def downgrade() -> None:
    # Rename episode_id column back to podcast_episode
    op.alter_column('books', 'episode_id', new_column_name='podcast_episode')
    # ### end Alembic commands ### 