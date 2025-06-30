"""remove_unique_constraint_on_goodreads_url

Revision ID: 6b81df32177d
Revises: 239ce4354440
Create Date: 2025-06-30 09:51:29.444061

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6b81df32177d'
down_revision = '239ce4354440'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove the unique constraint on goodreads_url
    op.drop_constraint('books_goodreads_url_key', 'books', type_='unique')


def downgrade() -> None:
    # Re-add the unique constraint on goodreads_url
    op.create_unique_constraint('books_goodreads_url_key', 'books', ['goodreads_url']) 