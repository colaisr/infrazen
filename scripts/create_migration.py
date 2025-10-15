#!/usr/bin/env python3
"""
Helper script to create new Alembic migrations
Usage: python scripts/create_migration.py "Add new table"
"""
import sys
import os
import subprocess

def create_migration(message):
    """Create a new Alembic migration with the given message"""
    if not message:
        print("Error: Migration message is required")
        print("Usage: python scripts/create_migration.py \"Add new table\"")
        sys.exit(1)
    
    # Set up environment
    os.environ['DATABASE_URL'] = 'mysql+pymysql://infrazen_user:infrazen_password@localhost:3306/infrazen_dev?charset=utf8mb4'
    
    # Create the migration
    cmd = ['python3', '-m', 'alembic', 'revision', '--autogenerate', '-m', message]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Migration created successfully!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error creating migration: {e}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/create_migration.py \"Migration message\"")
        sys.exit(1)
    
    message = sys.argv[1]
    create_migration(message)
