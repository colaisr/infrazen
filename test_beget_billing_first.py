#!/usr/bin/env python3
"""
Test Beget billing-first sync implementation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.providers.plugins.beget import BegetProviderPlugin
import json
from datetime import datetime

def test_beget_billing_first():
    """Test Beget billing-first implementation"""

    # Real credentials from database
    credentials = {
        'username': "colaiswv",
        'password': "Kok5489103",
        'api_url': "https://api.beget.com"
    }

    print(f"Testing Beget billing-first sync for user: {credentials['username']}")
    print("=" * 60)

    # Create plugin instance
    plugin = BegetProviderPlugin(
        provider_id=1,
        credentials=credentials,
        config={'connection_name': 'Beget- cola'}
    )

    try:
        # Test connection first
        print("\n1. TESTING CONNECTION...")
        connection_result = plugin.test_connection()
        print(f"Connection result: {'SUCCESS' if connection_result['success'] else 'FAILED'}")
        if not connection_result['success']:
            print(f"Error: {connection_result.get('message', 'Unknown error')}")
            return

        # Perform billing-first sync
        print("\n2. PERFORMING BILLING-FIRST SYNC...")
        print("This will execute the 4 phases:")
        print("  Phase 1: Billing Data Collection")
        print("  Phase 2: Resource Discovery with Cost Filtering")
        print("  Phase 3: Resource Processing and Unification")
        print("  Phase 4: Cost Validation")

        sync_result = plugin.sync_resources()

        print(f"\nSYNC RESULT: {'SUCCESS' if sync_result.success else 'FAILED'}")
        print(f"Message: {sync_result.message}")
        print(f"Resources synced: {sync_result.resources_synced}")
        print(f"Total cost: {sync_result.total_cost:.2f} RUB/day")

        if sync_result.success:
            sync_data = sync_result.data

            # Show billing phases
            phases = sync_data.get('billing_first_phases', {})
            print("\nBILLING-FIRST PHASES:")
            print(f"  ✓ Phase 1 - Billing Collected: {phases.get('phase_1_billing_collected', False)}")
            print(f"  ✓ Phase 2 - Paid Resources Found: {phases.get('phase_2_paid_resources_found', 0)}")
            print(f"  ✓ Phase 3 - Resources Unified: {phases.get('phase_3_resources_unified', 0)}")
            print(f"  ✓ Phase 4 - Costs Validated: {phases.get('phase_4_costs_validated', False)}")

            # Show account billing data
            account_billing = sync_data.get('account_billing', {})
            print("\nACCOUNT BILLING DATA:")
            print(f"  Account ID: {account_billing.get('account_id', 'N/A')}")
            print(f"  Balance: {account_billing.get('balance', 0):.2f} RUB")
            print(f"  Daily Rate: {account_billing.get('daily_rate', 0):.2f} RUB/day")
            print(f"  Monthly Rate: {account_billing.get('monthly_rate', 0):.2f} RUB/month")
            print(f"  Plan: {account_billing.get('plan_name', 'Unknown')}")

            # Show cost validation
            billing_validation = sync_data.get('billing_validation', {})
            print("\nCOST VALIDATION:")
            print(f"  Status: {'✓ PASSED' if billing_validation.get('valid', False) else '✗ FAILED'}")
            print(f"  Calculated Total: {billing_validation.get('total_calculated', 0):.2f} RUB/day")
            print(f"  Account Daily Rate: {billing_validation.get('account_daily_rate', 0):.2f} RUB/day")
            print(f"  Difference: {billing_validation.get('difference', 0):.2f} RUB/day")
            print(f"  Tolerance: {billing_validation.get('tolerance_percent', 0)}%")

            if not billing_validation.get('valid', False):
                issues = billing_validation.get('issues', [])
                print(f"  Issues: {issues}")

            # Show resources
            resources = sync_data.get('resources', [])
            print("\nRESOURCES INCLUDED (ONLY PAID):")
            for resource in resources:
                resource_data = resource.to_dict() if hasattr(resource, 'to_dict') else resource
                print(f"  • {resource_data.get('resource_name', 'Unknown')} ({resource_data.get('resource_type', 'unknown')}) - {resource_data.get('effective_cost', 0):.2f} RUB/day")

            # Summary
            print("\nSUMMARY:")
            print(f"  Total Paid Resources: {len(resources)}")
            print(f"  Total Daily Cost: {sync_result.total_cost:.2f} RUB/day")
            print(f"  All resources have actual costs: {'✓ YES' if all(r.get('effective_cost', 0) > 0 for r in [res.to_dict() if hasattr(res, 'to_dict') else res for res in resources]) else '✗ NO'}")
        else:
            print(f"Sync failed with errors: {sync_result.errors}")

    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_beget_billing_first()
