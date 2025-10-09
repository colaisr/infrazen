#!/usr/bin/env python3
"""
Script to update Beget credentials
Replace the credentials below with your actual Beget login details
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
import json

# REPLACE THESE WITH YOUR ACTUAL BEGET CREDENTIALS
NEW_USERNAME = "your_beget_username_here"
NEW_PASSWORD = "your_beget_password_here"

def update_credentials():
    app = create_app()
    with app.app_context():
        from app.core.models.provider import CloudProvider

        provider = CloudProvider.query.get(1)  # Beget provider ID
        if provider:
            print('Updating Beget credentials...')

            # Update with new credentials
            new_creds = {
                'username': NEW_USERNAME,
                'password': NEW_PASSWORD,
                'api_url': 'https://api.beget.com'
            }

            provider.credentials = json.dumps(new_creds)
            provider.sync_status = 'pending'
            provider.sync_error = None

            from app import db
            db.session.commit()

            print('✅ Credentials updated successfully!')
            print(f'Username: {NEW_USERNAME}')
            print('Password: [HIDDEN]')
            print()
            print('You can now try syncing again from the web interface.')
        else:
            print('❌ Beget provider not found (ID: 1)')

if __name__ == '__main__':
    print('🔧 Beget Credentials Update Script')
    print('=' * 40)
    print()
    print('Before running this script:')
    print('1. Edit this file and replace NEW_USERNAME and NEW_PASSWORD with your actual Beget credentials')
    print('2. Save the file')
    print('3. Run: python3 update_beget_credentials.py')
    print()

    if NEW_USERNAME == "your_beget_username_here" or NEW_PASSWORD == "your_beget_password_here":
        print('❌ Please edit this file first and replace the placeholder credentials!')
        sys.exit(1)

    update_credentials()
