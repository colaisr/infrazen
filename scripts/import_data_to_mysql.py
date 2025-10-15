#!/usr/bin/env python3
"""
Import JSON export data into MySQL database
"""
import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.core.database import db
from sqlalchemy import text, inspect

def import_json_to_mysql(json_path):
    """Import JSON data to MySQL"""
    print(f"🔄 Reading export file: {json_path}")
    
    if not os.path.exists(json_path):
        print(f"❌ Export file not found: {json_path}")
        return False
    
    with open(json_path, 'r', encoding='utf-8') as f:
        export_data = json.load(f)
    
    print(f"📊 Export created: {export_data.get('exported_at')}")
    print(f"   Source: {export_data.get('source_database')}")
    
    tables = export_data.get('tables', {})
    print(f"   Tables to import: {len(tables)}")
    
    # Define import order (respecting foreign keys)
    # Import order aligned to actual exported tables and FK relationships
    # Adjust as needed if schema evolves
    import_order = [
        'users',
        'provider_catalog',
        'cloud_providers',
        'sync_snapshots',
        'resources',
        'resource_states',
        'resource_tags',
        'provider_admin_credentials',
        'provider_prices',
        'price_history',
        'optimization_recommendations',
        'unrecognized_resources',
        'resource_metrics',
        'resource_logs',
        'resource_components',
        'resource_usage_summary',
        'cost_trends',
        'cost_allocations',
        'price_comparison_recommendations'
    ]
    
    # Add any tables not in the predefined order
    for table_name in tables.keys():
        if table_name not in import_order:
            import_order.append(table_name)
    
    app = create_app()
    
    with app.app_context():
        print("\n🔄 Starting import to MySQL...")
        
        total_imported = 0
        
        # Optional: limit to a single table
        only_table = os.getenv('IMPORT_ONLY')
        for table_name in import_order:
            if only_table and table_name != only_table:
                continue
            if table_name not in tables:
                continue
            
            table_data = tables[table_name]
            
            if 'error' in table_data:
                print(f"   ⚠️  Skipping {table_name} (had export error)")
                continue
            
            rows = table_data.get('data', [])
            if not rows:
                print(f"   ℹ️  Skipping {table_name} (no data)")
                continue
            
            print(f"   Importing {table_name}...", end=' ')
            
            try:
                # Discover actual table columns in target DB and filter unknowns
                inspector = inspect(db.engine)
                db_columns = {c['name'] for c in inspector.get_columns(table_name)}
                if not db_columns:
                    print(f"\n      ⚠️  No columns found in DB for {table_name}, skipping")
                    continue
                # Use only columns that exist in target DB
                columns = [c for c in rows[0].keys() if c in db_columns]
                placeholders = ', '.join([f':{col}' for col in columns])
                column_names = ', '.join(columns)
                
                # Prepare insert statement
                insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
                
                # Import rows
                imported_count = 0
                for row in rows:
                    try:
                        # Convert datetime strings back to datetime objects if needed and filter keys
                        processed_row = {}
                        for key, value in row.items():
                            if key not in db_columns:
                                continue
                            # Handle datetime fields
                            if key in ['created_at', 'updated_at', 'last_login', 'last_sync', 
                                      'synced_at', 'sync_started_at', 'sync_completed_at', 'timestamp']:
                                if value and isinstance(value, str):
                                    try:
                                        processed_row[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                    except:
                                        processed_row[key] = value
                                else:
                                    processed_row[key] = value
                            else:
                                processed_row[key] = value
                        
                        db.session.execute(text(insert_sql), processed_row)
                        imported_count += 1
                    except Exception as row_error:
                        print(f"\n      ⚠️  Error importing row: {row_error}")
                        # Continue with next row
                        continue
                
                db.session.commit()
                total_imported += imported_count
                print(f"✅ {imported_count}/{len(rows)} rows")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                db.session.rollback()
        
        print(f"\n✅ Import completed!")
        print(f"   Total rows imported: {total_imported}")
        
        # Verify import
        print("\n📊 Verifying import...")
        for table_name in import_order:
            if table_name not in tables:
                continue
            
            try:
                result = db.session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                expected = tables[table_name].get('row_count', 0)
                status = "✅" if count == expected else "⚠️"
                print(f"   {status} {table_name}: {count} rows (expected {expected})")
            except:
                pass
    
    return True

def main():
    """Main import function"""
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sqlite_export.json')
    
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    flags = {a for a in sys.argv[1:] if a.startswith('-')}
    if len(args) > 0:
        json_path = args[0]
    
    print("=" * 60)
    print("JSON to MySQL Import Tool")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: Make sure MySQL database is initialized first!")
    print("   Run: python init_database.py")
    print()

    non_interactive = ('--yes' in flags) or (os.getenv('IMPORT_YES') == '1')
    if not non_interactive:
        try:
            input("Press Enter to continue with import (or Ctrl+C to cancel)...")
        except EOFError:
            # Default to continue in non-interactive environments
            print("\nℹ️  Non-interactive environment detected. Continuing import...")
    
    success = import_json_to_mysql(json_path)
    
    if success:
        print("\n✅ Data successfully imported to MySQL")
    else:
        print("\n❌ Import failed")
        sys.exit(1)

if __name__ == "__main__":
    main()

