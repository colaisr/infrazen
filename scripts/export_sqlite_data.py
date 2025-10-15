#!/usr/bin/env python3
"""
Export SQLite database to JSON for migration to MySQL
"""
import os
import sys
import json
import sqlite3
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def serialize_value(value):
    """Convert value to JSON-serializable format"""
    if isinstance(value, (datetime,)):
        return value.isoformat()
    elif isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore')
    return value

def export_sqlite_to_json(sqlite_path, output_path):
    """Export SQLite database to JSON"""
    print(f"🔄 Connecting to SQLite database: {sqlite_path}")
    
    if not os.path.exists(sqlite_path):
        print(f"❌ SQLite database not found: {sqlite_path}")
        return False
    
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"📊 Found {len(tables)} tables to export")
    
    export_data = {
        'exported_at': datetime.now().isoformat(),
        'source_database': sqlite_path,
        'tables': {}
    }
    
    total_rows = 0
    
    for table_name in tables:
        print(f"   Exporting table: {table_name}...", end=' ')
        
        try:
            # Get all rows from table
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            # Convert rows to dictionaries
            table_data = []
            for row in rows:
                row_dict = {}
                for key in row.keys():
                    row_dict[key] = serialize_value(row[key])
                table_data.append(row_dict)
            
            export_data['tables'][table_name] = {
                'row_count': len(table_data),
                'data': table_data
            }
            
            total_rows += len(table_data)
            print(f"✅ {len(table_data)} rows")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            export_data['tables'][table_name] = {
                'error': str(e),
                'row_count': 0,
                'data': []
            }
    
    conn.close()
    
    # Write to JSON file
    print(f"\n💾 Writing export to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Export completed successfully!")
    print(f"   Total rows exported: {total_rows}")
    print(f"   Tables exported: {len(tables)}")
    
    return True

def main():
    """Main export function"""
    # Default paths
    sqlite_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'dev.db')
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sqlite_export.json')
    
    # Allow custom paths via command line
    if len(sys.argv) > 1:
        sqlite_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    
    print("=" * 60)
    print("SQLite to JSON Export Tool")
    print("=" * 60)
    print()
    
    success = export_sqlite_to_json(sqlite_path, output_path)
    
    if success:
        print("\n✅ Export file ready for MySQL import")
        print(f"   File: {output_path}")
    else:
        print("\n❌ Export failed")
        sys.exit(1)

if __name__ == "__main__":
    main()

