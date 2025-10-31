#!/usr/bin/env python3
from app import create_app
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    from app.core.database import db
    insp = inspect(db.engine)
    
    if 'resource_states' in insp.get_table_names():
        columns = insp.get_columns('resource_states')
        print("resource_states table columns:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")
    else:
        print("resource_states table does NOT exist!")

