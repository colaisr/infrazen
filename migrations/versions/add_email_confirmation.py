"""Add email confirmation fields to users table

Revision ID: add_email_confirmation
Revises: 
Create Date: 2024-10-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a9c8e7f2b4d'
down_revision = 'f2f8e153a198'
branch_label = None
depends_on = None


def upgrade():
    # Add email confirmation columns to users table
    op.add_column('users', sa.Column('email_confirmed', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('email_confirmation_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_confirmation_sent_at', sa.DateTime(), nullable=True))
    
    # For existing Google OAuth users who have google_verified_email=True, set email_confirmed=True
    op.execute("""
        UPDATE users 
        SET email_confirmed = 1 
        WHERE google_verified_email = 1
    """)


def downgrade():
    # Remove email confirmation columns
    op.drop_column('users', 'email_confirmation_sent_at')
    op.drop_column('users', 'email_confirmation_token')
    op.drop_column('users', 'email_confirmed')

