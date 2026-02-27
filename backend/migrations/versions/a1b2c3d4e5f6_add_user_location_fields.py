"""Add user location fields

Revision ID: a1b2c3d4e5f6
Revises: 9324946836a4
Create Date: 2026-02-23 06:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9324946836a4'
branch_labels = None
depends_on = None


def upgrade():
    # Add location column to users table
    op.add_column('users', sa.Column('location', sa.String(length=255), nullable=True))
    # Add preferred_work_type column to users table
    op.add_column('users', sa.Column('preferred_work_type', sa.String(length=50), nullable=True))


def downgrade():
    # Drop preferred_work_type column
    op.drop_column('users', 'preferred_work_type')
    # Drop location column
    op.drop_column('users', 'location')
