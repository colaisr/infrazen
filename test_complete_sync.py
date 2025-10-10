#!/usr/bin/env python3
"""
Test complete sync with CPU/memory statistics
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.providers.sync_orchestrator import sync_orchestrator

def test_complete_sync():
    """Test complete sync for Beget provider"""
    
    print("Testing complete sync for Beget provider...")
    
    try:
        # Sync the Beget provider (ID 1)
        result = sync_orchestrator.sync_provider(1, 'manual')
        
        print(f"Sync result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Message: {result['message']}")
        
        if result['success']:
            print(f"Resources synced: {result.get('resources_synced', 0)}")
            print(f"Total cost: {result.get('total_cost', 0):.2f} RUB/day")
            print(f"Sync snapshot ID: {result.get('sync_snapshot_id', 'N/A')}")
        
    except Exception as e:
        print(f"Sync failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complete_sync()


