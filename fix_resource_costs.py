#!/usr/bin/env python3
"""
Fix cost data for existing resources by setting daily cost baseline
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.core.models import Resource

def fix_resource_costs():
    app = create_app()
    with app.app_context():
        print('🔧 Fixing cost data for existing resources...')

        # Get all Beget resources
        resources = Resource.query.filter_by(provider_id=1).all()

        print(f'📊 Found {len(resources)} Beget resources')

        fixed_count = 0
        for resource in resources:
            try:
                # Set daily cost baseline for FinOps analysis
                resource.set_daily_cost_baseline(
                    original_cost=resource.effective_cost,
                    period=resource.billing_period,
                    frequency='recurring'
                )

                print(f'✅ Fixed {resource.resource_type}: {resource.resource_name} - {resource.effective_cost} {resource.currency}')
                fixed_count += 1

            except Exception as e:
                print(f'❌ Failed to fix {resource.resource_name}: {e}')

        # Commit all changes
        from app import db
        db.session.commit()

        print(f'\n🎉 Fixed cost data for {fixed_count}/{len(resources)} resources')
        print('Now resources should show proper cost information in the UI!')

if __name__ == '__main__':
    fix_resource_costs()
