#!/usr/bin/env python3
"""
Test CPU/Memory statistics restoration in Beget billing-first implementation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.providers.plugins.beget import BegetProviderPlugin
import json
from datetime import datetime

def test_cpu_memory_restore():
    """Test that CPU/Memory statistics are collected and attached to resources"""

    # Real credentials from database
    credentials = {
        'username': "colaiswv",
        'password': "Kok5489103",
        'api_url': "https://api.beget.com"
    }

    print(f"Testing CPU/Memory statistics restoration for user: {credentials['username']}")
    print("=" * 60)

    # Create plugin instance
    plugin = BegetProviderPlugin(
        provider_id=1,
        credentials=credentials,
        config={'connection_name': 'Beget- cola'}
    )

    try:
        # Perform billing-first sync with CPU/memory statistics
        print("\n1. PERFORMING BILLING-FIRST SYNC WITH CPU/MEMORY STATS...")
        
        sync_result = plugin.sync_resources()

        print(f"\nSYNC RESULT: {'SUCCESS' if sync_result.success else 'FAILED'}")
        print(f"Message: {sync_result.message}")
        print(f"Resources synced: {sync_result.resources_synced}")

        if sync_result.success:
            sync_data = sync_result.data

            # Check CPU/memory statistics
            cpu_statistics = sync_data.get('cpu_statistics', {})
            memory_statistics = sync_data.get('memory_statistics', {})
            
            print("\nCPU/MEMORY STATISTICS:")
            print(f"CPU statistics available: {bool(cpu_statistics)}")
            print(f"Memory statistics available: {bool(memory_statistics)}")
            
            if cpu_statistics:
                cpu_stats_data = cpu_statistics.get('cpu_statistics', {})
                print(f"CPU data for VPS: {list(cpu_stats_data.keys())}")
                for vps_id, stats in cpu_stats_data.items():
                    vps_name = stats.get('vps_name', 'Unknown')
                    cpu_data = stats.get('cpu_statistics', {})
                    print(f"  {vps_name}: avg={cpu_data.get('avg_cpu_usage', 0):.2f}%, max={cpu_data.get('max_cpu_usage', 0):.2f}%")
            
            if memory_statistics:
                memory_stats_data = memory_statistics.get('memory_statistics', {})
                print(f"Memory data for VPS: {list(memory_stats_data.keys())}")
                for vps_id, stats in memory_stats_data.items():
                    vps_name = stats.get('vps_name', 'Unknown')
                    memory_data = stats.get('memory_statistics', {})
                    print(f"  {vps_name}: avg={memory_data.get('avg_memory_usage_mb', 0):.2f}MB ({memory_data.get('memory_usage_percent', 0):.2f}%)")

            # Check resources for attached performance data
            resources = sync_data.get('resources', [])
            print(f"\nRESOURCES WITH PERFORMANCE DATA:")
            for resource in resources:
                resource_data = resource.to_dict() if hasattr(resource, 'to_dict') else resource
                resource_name = resource_data.get('resource_name', 'Unknown')
                resource_type = resource_data.get('resource_type', 'unknown')
                
                # Check for CPU/memory tags
                tags = resource_data.get('tags', {})
                has_cpu_data = 'cpu_avg_usage' in tags
                has_memory_data = 'memory_avg_usage_mb' in tags
                
                print(f"  {resource_name} ({resource_type}):")
                print(f"    CPU data: {'✓' if has_cpu_data else '✗'}")
                print(f"    Memory data: {'✓' if has_memory_data else '✗'}")
                
                if has_cpu_data:
                    print(f"    CPU avg: {tags.get('cpu_avg_usage', 0)}%")
                if has_memory_data:
                    print(f"    Memory avg: {tags.get('memory_avg_usage_mb', 0)}MB ({tags.get('memory_usage_percent', 0)}%)")

            # Summary
            resources_with_performance = sum(1 for r in resources if 
                ('cpu_avg_usage' in (r.to_dict() if hasattr(r, 'to_dict') else r).get('tags', {})) or
                ('memory_avg_usage_mb' in (r.to_dict() if hasattr(r, 'to_dict') else r).get('tags', {})))
            
            print(f"\nSUMMARY:")
            print(f"  Total resources: {len(resources)}")
            print(f"  Resources with performance data: {resources_with_performance}")
            print(f"  CPU statistics collected: {bool(cpu_statistics)}")
            print(f"  Memory statistics collected: {bool(memory_statistics)}")
            
        else:
            print(f"Sync failed with errors: {sync_result.errors}")

    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cpu_memory_restore()


