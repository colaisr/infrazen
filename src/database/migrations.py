"""
Database migration script for Beget integration
Run this to create the necessary tables for Beget provider
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

def create_app():
    """Create Flask app for migrations"""
    app = Flask(__name__)
    
    # Database configuration
    import os
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src', 'database', 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    return app

def create_beget_tables():
    """Create all Beget-related database tables"""
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        # Import all Beget models
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from models.beget import (
            BegetConnection, 
            BegetResource, 
            BegetDomain, 
            BegetDatabase, 
            BegetFTPAccount
        )
        
        # Create all tables
        try:
            db.create_all()
            print("✅ Successfully created Beget database tables:")
            print("   - beget_connections")
            print("   - beget_resources") 
            print("   - beget_domains")
            print("   - beget_databases")
            print("   - beget_ftp_accounts")
            return True
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False

def drop_beget_tables():
    """Drop all Beget-related database tables"""
    app = create_app()
    db = SQLAlchemy(app)
    
    with app.app_context():
        # Import all Beget models
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from models.beget import (
            BegetConnection, 
            BegetResource, 
            BegetDomain, 
            BegetDatabase, 
            BegetFTPAccount
        )
        
        try:
            db.drop_all()
            print("✅ Successfully dropped Beget database tables")
            return True
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        drop_beget_tables()
    else:
        create_beget_tables()
