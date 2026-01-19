"""add shared_with_user_ids to watchlist and report

Revision ID: 69c4e900891b
Revises: 0539f9bd9bcc
Create Date: 2025-11-27 16:03:32.213831

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69c4e900891b'
down_revision: Union[str, Sequence[str], None] = '0539f9bd9bcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add shared_with_user_ids to asset_watchlist table
    op.add_column('asset_watchlist', sa.Column('shared_with_user_ids', sa.JSON(), nullable=True))
    
    # Add shared_with_user_ids to reports table
    op.add_column('reports', sa.Column('shared_with_user_ids', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove shared_with_user_ids from reports table
    op.drop_column('reports', 'shared_with_user_ids')
    
    # Remove shared_with_user_ids from asset_watchlist table
    op.drop_column('asset_watchlist', 'shared_with_user_ids')
