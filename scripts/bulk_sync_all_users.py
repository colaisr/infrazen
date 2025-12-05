#!/usr/bin/env python3
"""
Bulk Sync Script - Synchronize all organizations

This script triggers a complete synchronization for all organizations that have
auto-sync enabled providers. It's designed to be run as a cron job or manually.

Note: The script now syncs by organization instead of by user to avoid duplicate
syncs when multiple users belong to the same organization.

Usage:
    python scripts/bulk_sync_all_users.py [--sync-type TYPE] [--dry-run] [--verbose]

Arguments:
    --sync-type TYPE    Type of sync: scheduled (default), manual, or api
    --dry-run          Show which organizations would be synced without executing
    --verbose          Show detailed output during sync
    --quiet            Minimal output (only errors and summary)

Examples:
    # Run scheduled sync (default)
    python scripts/bulk_sync_all_users.py

    # Run manual sync with verbose output
    python scripts/bulk_sync_all_users.py --sync-type manual --verbose

    # Dry run to see which organizations would be synced
    python scripts/bulk_sync_all_users.py --dry-run

Cron job setup (daily at 8:00 AM MSK):
    0 8 * * * cd /opt/infrazen && /opt/infrazen/venv/bin/python scripts/bulk_sync_all_users.py --sync-type scheduled >> /var/log/infrazen_bulk_sync.log 2>&1
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.core.services.bulk_sync_service import BulkSyncService
from app.core.models.organization import Organization
from app.core.models.provider import CloudProvider

def setup_logging(verbose=False, quiet=False):
    """Setup logging configuration"""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from other libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def print_header(text, char='='):
    """Print a formatted header"""
    print(f"\n{char * 70}")
    print(f" {text}")
    print(f"{char * 70}")

def print_org_result(result, index, total):
    """Print formatted organization result"""
    status = result.get('status', 'unknown')
    org_name = result.get('organization_name', 'Unknown')
    
    # Status emoji and color
    status_map = {
        'success': ('✓', '\033[92m'),  # Green
        'failed': ('✗', '\033[91m'),   # Red
        'error': ('✗', '\033[91m'),    # Red
        'skipped': ('○', '\033[93m')   # Yellow
    }
    emoji, color = status_map.get(status, ('?', '\033[0m'))
    reset = '\033[0m'
    
    # Build status line
    line = f"[{index}/{total}] {color}{emoji}{reset} {org_name}"
    
    if status == 'success':
        providers = result.get('successful_providers', 0)
        resources = result.get('resources_found', 0)
        duration = result.get('duration_seconds', 0)
        line += f" - {providers} providers, {resources} resources ({duration:.1f}s)"
    elif status in ['failed', 'error']:
        error = result.get('error', 'Unknown error')
        line += f" - Error: {error}"
    elif status == 'skipped':
        reason = result.get('reason', 'Unknown reason')
        line += f" - {reason}"
    
    print(line)

def run_dry_run():
    """Show which organizations would be synced without executing"""
    print_header("Bulk Sync - Dry Run", '=')
    
    service = BulkSyncService()
    orgs = service.get_eligible_organizations()
    
    if not orgs:
        print("No eligible organizations found for bulk sync.")
        return
    
    print(f"\nFound {len(orgs)} eligible organizations for synchronization:\n")
    
    for idx, org in enumerate(orgs, 1):
        # Get provider count
        provider_count = CloudProvider.query.filter_by(
            organization_id=org.id,
            auto_sync=True,
            is_active=True,
            is_deleted=False
        ).count()
        
        status_icon = "✓" if provider_count > 0 else "○"
        status_text = f"{provider_count} providers" if provider_count > 0 else "No auto-sync providers"
        
        print(f"  [{idx:2d}] {status_icon} {org.name:40s} (ID: {org.id:3d}) - {status_text}")
    
    print(f"\n{'-' * 70}")
    orgs_with_providers = sum(1 for o in orgs if CloudProvider.query.filter_by(
        organization_id=o.id, auto_sync=True, is_active=True, is_deleted=False
    ).count() > 0)
    print(f"Summary: {orgs_with_providers} organizations with providers, {len(orgs) - orgs_with_providers} would be skipped")

def run_bulk_sync(sync_type='scheduled', verbose=False, quiet=False):
    """Execute bulk sync for all organizations"""
    if not quiet:
        print_header(f"Bulk Sync - {sync_type.upper()}", '=')
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create service and execute sync
    service = BulkSyncService()
    result = service.sync_all_organizations(sync_type=sync_type)
    
    # Print results
    if not quiet:
        print_header("Sync Results", '-')
        
        # Support both old (user_results) and new (organization_results) format for backward compatibility
        org_results = result.get('organization_results') or result.get('user_results', [])
        if org_results:
            total = len(org_results)
            for idx, org_result in enumerate(org_results, 1):
                print_org_result(org_result, idx, total)
    
    # Print summary
    print_header("Summary", '=')
    # Support both old and new format for backward compatibility
    total_orgs = result.get('total_organizations') or result.get('total_users', 0)
    successful = result.get('successful_organizations') or result.get('successful_users', 0)
    failed = result.get('failed_organizations') or result.get('failed_users', 0)
    skipped = result.get('skipped_organizations') or result.get('skipped_users', 0)
    
    print(f"Total organizations: {total_orgs}")
    print(f"Successful:          {successful}")
    print(f"Failed:              {failed}")
    print(f"Skipped:             {skipped}")
    print(f"Duration:            {result.get('duration_seconds', 0):.1f} seconds")
    print(f"Completed at:        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('=' * 70)
    
    # Exit with appropriate code
    if failed > 0:
        sys.exit(1)  # Some organizations failed
    elif successful == 0 and skipped == 0:
        sys.exit(2)  # No organizations processed
    else:
        sys.exit(0)  # Success

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Bulk synchronization for all organizations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run scheduled sync
  %(prog)s --sync-type manual --verbose # Run manual sync with details
  %(prog)s --dry-run                    # Show organizations without syncing
        """
    )
    
    parser.add_argument(
        '--sync-type',
        choices=['scheduled', 'manual', 'api'],
        default='scheduled',
        help='Type of sync to execute (default: scheduled)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show which organizations would be synced without executing'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output during sync'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output (only errors and summary)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose, quiet=args.quiet)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            if args.dry_run:
                run_dry_run()
            else:
                run_bulk_sync(
                    sync_type=args.sync_type,
                    verbose=args.verbose,
                    quiet=args.quiet
                )
        except KeyboardInterrupt:
            print("\n\nSync interrupted by user.")
            sys.exit(130)
        except Exception as e:
            logging.error(f"Bulk sync failed with exception: {e}", exc_info=True)
            print(f"\n\nERROR: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()





















