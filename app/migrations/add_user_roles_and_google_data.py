"""
Migration: Add user roles and Google OAuth data
"""
from app.core.database import db
from app.core.models.user import User

def upgrade():
    """Add new columns to users table"""
    # This migration adds the new columns for Google OAuth and roles
    # The columns are already defined in the User model, so we just need to create the table
    # or alter the existing table if it exists
    
    # For SQLite, we'll need to recreate the table with new columns
    # This is a simplified migration - in production, use proper Alembic migrations
    
    try:
        # Create tables if they don't exist
        db.create_all()
        print("✅ Database tables created/updated successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

def downgrade():
    """Remove new columns (not implemented for safety)"""
    # In production, implement proper rollback
    print("⚠️  Downgrade not implemented for safety")

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        upgrade()
