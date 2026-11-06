"""merge heads

Revision ID: 0539f9bd9bcc
Revises: 96c5a12c92d3, e1dd2875d480
Create Date: 2025-11-27 16:02:37.038354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0539f9bd9bcc'
down_revision: Union[str, Sequence[str], None] = ('96c5a12c92d3', 'e1dd2875d480')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
