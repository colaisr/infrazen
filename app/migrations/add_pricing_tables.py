"""
Migration: Add pricing tables for multi-provider price comparison
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.core.database import db
from app.core.models.pricing import ProviderPrice, PriceHistory, PriceComparisonRecommendation

def run_migration():
    """Run the migration to create pricing tables"""
    
    app = create_app()
    
    with app.app_context():
        print("Starting pricing tables migration...")
        
        try:
            # Create all tables
            db.create_all()
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = ['provider_prices', 'price_history', 'price_comparison_recommendations']
            created_tables = [table for table in expected_tables if table in tables]
            
            if len(created_tables) == len(expected_tables):
                print(f"✅ Successfully created {len(created_tables)} pricing tables:")
                for table in created_tables:
                    print(f"   - {table}")
                
                # Check indexes
                print("\n📊 Checking indexes...")
                for table_name in created_tables:
                    indexes = inspector.get_indexes(table_name)
                    print(f"   {table_name}: {len(indexes)} indexes")
                    for idx in indexes:
                        print(f"     - {idx['name']}: {', '.join(idx['column_names'])}")
                
                print(f"\n🎉 Migration completed successfully at {datetime.now()}")
                return True
            else:
                missing_tables = set(expected_tables) - set(created_tables)
                print(f"❌ Migration failed: Missing tables: {missing_tables}")
                return False
                
        except Exception as e:
            print(f"❌ Migration failed with error: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
