#!/usr/bin/env python3
"""
Price Sync Script - Synchronize pricing catalogs for all enabled providers

This script updates the pricing catalog from all enabled cloud providers that have
a pricing API. It's designed to be run as a cron job or manually.

Usage:
    python scripts/sync_all_prices.py [--provider TYPE] [--dry-run] [--verbose] [--quiet]

Arguments:
    --provider TYPE    Sync only specific provider (yandex, selectel, beget)
    --dry-run          Show which providers would be synced without executing
    --verbose          Show detailed output during sync
    --quiet            Minimal output (only errors and summary)

Examples:
    # Sync all providers (default)
    python scripts/sync_all_prices.py

    # Sync only Yandex Cloud
    python scripts/sync_all_prices.py --provider yandex

    # Dry run to see which providers would be synced
    python scripts/sync_all_prices.py --dry-run

    # Verbose output
    python scripts/sync_all_prices.py --verbose

Cron job setup (daily at 3 AM):
    0 3 * * * cd /path/to/infrazen && ./venv/bin/python scripts/sync_all_prices.py --quiet
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.core.services.price_update_service import PriceUpdateService
from app.core.models.provider_catalog import ProviderCatalog

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
    logging.getLogger('requests').setLevel(logging.WARNING)

def print_header(text, char='='):
    """Print a formatted header"""
    print(f"\n{char * 80}")
    print(f" {text}")
    print(f"{char * 80}")

def print_provider_result(result, index, total):
    """Print formatted provider result"""
    status = result.get('status', 'unknown')
    provider = result.get('provider', 'Unknown')
    
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
    line = f"[{index}/{total}] {color}{emoji}{reset} {provider:20s}"
    
    if status == 'success':
        records = result.get('records', 0)
        duration = result.get('duration', 0)
        line += f" - {records:4d} records ({duration:6.1f}s)"
    elif status in ['failed', 'error']:
        error = result.get('error', 'Unknown error')
        line += f" - Error: {error}"
    elif status == 'skipped':
        reason = result.get('reason', 'Unknown reason')
        line += f" - {reason}"
    
    print(line)

def run_dry_run(provider_type=None):
    """Show which providers would be synced without executing"""
    print_header("Price Sync - Dry Run", '=')
    
    query = ProviderCatalog.query.filter_by(
        is_enabled=True,
        has_pricing_api=True
    )
    
    if provider_type:
        query = query.filter_by(provider_type=provider_type)
    
    providers = query.all()
    
    if not providers:
        if provider_type:
            print(f"No enabled provider found for type: {provider_type}")
        else:
            print("No enabled providers with pricing API found.")
        return
    
    print(f"\nFound {len(providers)} provider(s) for price synchronization:\n")
    
    for idx, provider in enumerate(providers, 1):
        from app.core.models.pricing import ProviderPrice
        price_count = ProviderPrice.query.filter_by(provider=provider.provider_type).count()
        
        last_sync = provider.last_price_sync.strftime('%Y-%m-%d %H:%M') if provider.last_price_sync else 'Never'
        
        status_icon = "✓" if price_count > 0 else "○"
        status_text = f"{price_count} prices, last sync: {last_sync}"
        
        print(f"  [{idx:2d}] {status_icon} {provider.display_name:30s} ({provider.provider_type:10s}) - {status_text}")
    
    print(f"\n{'-' * 80}")
    total_prices = sum(ProviderPrice.query.filter_by(provider=p.provider_type).count() for p in providers)
    print(f"Summary: {len(providers)} provider(s), {total_prices} total prices in database")

def run_price_sync(provider_type=None, verbose=False, quiet=False):
    """Execute price sync for providers"""
    if not quiet:
        if provider_type:
            print_header(f"Price Sync - {provider_type.upper()}", '=')
        else:
            print_header("Price Sync - All Providers", '=')
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get providers
    query = ProviderCatalog.query.filter_by(
        is_enabled=True,
        has_pricing_api=True
    )
    
    if provider_type:
        query = query.filter_by(provider_type=provider_type)
    
    providers = query.all()
    
    if not providers:
        if provider_type:
            print(f"❌ No enabled provider found for type: {provider_type}")
        else:
            print("❌ No enabled providers with pricing API found")
        sys.exit(2)
    
    # Create service
    price_service = PriceUpdateService()
    
    results = {
        'total_providers': len(providers),
        'successful_providers': 0,
        'failed_providers': 0,
        'provider_results': []
    }
    
    start_time = datetime.now()
    
    # Sync each provider
    for idx, provider in enumerate(providers, 1):
        provider_start = datetime.now()
        
        if not quiet:
            print(f"\n[{idx}/{len(providers)}] Syncing {provider.display_name}...")
        
        try:
            result = price_service.sync_provider_prices(provider.provider_type)
            duration = (datetime.now() - provider_start).total_seconds()
            
            if result.get('success'):
                results['successful_providers'] += 1
                records = result.get('records_synced', 0)
                
                results['provider_results'].append({
                    'provider': provider.display_name,
                    'provider_type': provider.provider_type,
                    'status': 'success',
                    'records': records,
                    'duration': duration
                })
                
                if not quiet:
                    print(f"✅ Success: {records} records synced in {duration:.1f}s")
            else:
                results['failed_providers'] += 1
                error = result.get('error', 'Unknown error')
                
                results['provider_results'].append({
                    'provider': provider.display_name,
                    'provider_type': provider.provider_type,
                    'status': 'failed',
                    'error': error
                })
                
                print(f"❌ Failed: {error}")
        
        except Exception as e:
            results['failed_providers'] += 1
            duration = (datetime.now() - provider_start).total_seconds()
            
            results['provider_results'].append({
                'provider': provider.display_name,
                'provider_type': provider.provider_type,
                'status': 'error',
                'error': str(e)
            })
            
            print(f"❌ Exception: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
    
    # Print results
    if not quiet:
        print_header("Sync Results", '-')
        
        for idx, result in enumerate(results['provider_results'], 1):
            print_provider_result(result, idx, len(results['provider_results']))
    
    # Print summary
    total_duration = (datetime.now() - start_time).total_seconds()
    total_records = sum(r.get('records', 0) for r in results['provider_results'] if r.get('status') == 'success')
    
    print_header("Summary", '=')
    print(f"Total providers:   {results['total_providers']}")
    print(f"Successful:        {results['successful_providers']}")
    print(f"Failed:            {results['failed_providers']}")
    print(f"Total records:     {total_records}")
    print(f"Duration:          {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
    print(f"Completed at:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('=' * 80)
    
    # Exit with appropriate code
    if results['failed_providers'] > 0 and results['successful_providers'] == 0:
        sys.exit(1)  # All failed
    elif results['failed_providers'] > 0:
        sys.exit(2)  # Some failed
    else:
        sys.exit(0)  # All successful

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Price catalog synchronization for cloud providers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Sync all providers
  %(prog)s --provider yandex        # Sync only Yandex Cloud
  %(prog)s --dry-run                # Show providers without syncing
  %(prog)s --verbose                # Detailed output
        """
    )
    
    parser.add_argument(
        '--provider',
        choices=['yandex', 'selectel', 'beget'],
        help='Sync only specific provider'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show which providers would be synced without executing'
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
                run_dry_run(provider_type=args.provider)
            else:
                run_price_sync(
                    provider_type=args.provider,
                    verbose=args.verbose,
                    quiet=args.quiet
                )
        except KeyboardInterrupt:
            print("\n\nSync interrupted by user.")
            sys.exit(130)
        except Exception as e:
            logging.error(f"Price sync failed with exception: {e}", exc_info=True)
            print(f"\n\nERROR: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()

