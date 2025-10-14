"""
Migration: Add Provider Admin Credentials Table
Purpose: Create table for storing system-level credentials for pricing data access
"""
import sys
import os

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import db
from app.core.models import ProviderAdminCredentials
from app import create_app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add provider admin credentials table"""
    try:
        logger.info("Starting migration: add_provider_admin_credentials")
        
        # Create app context
        app = create_app()
        
        with app.app_context():
            # Create the provider_admin_credentials table
            logger.info("Creating provider_admin_credentials table...")
            db.create_all()
            
            # Verify table creation
            with db.engine.connect() as conn:
                result = conn.execute(db.text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='provider_admin_credentials'"
                ))
                if result.fetchone():
                    logger.info("✓ provider_admin_credentials table created successfully")
                else:
                    logger.error("✗ Failed to create provider_admin_credentials table")
                    return False
            
            logger.info("Migration completed successfully!")
            return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)

