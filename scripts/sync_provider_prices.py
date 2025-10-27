#!/usr/bin/env python3
"""
Background price sync script for all providers
Can be run by cron or manually for scheduled price catalog updates
"""
import sys
import os
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.core.database import db
from app.core.models.provider_catalog import ProviderCatalog
from app.core.services.price_update_service import PriceUpdateService

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/price_sync.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def sync_all_providers():
    """Sync pricing data for all enabled providers"""
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("=" * 80)
            logger.info("Starting scheduled price sync for all providers")
            logger.info("=" * 80)
            
            # Get all enabled providers with pricing API
            providers = ProviderCatalog.query.filter_by(
                is_enabled=True,
                has_pricing_api=True
            ).all()
            
            if not providers:
                logger.warning("No enabled providers with pricing API found")
                return
            
            logger.info(f"Found {len(providers)} enabled providers to sync")
            
            # Initialize price update service
            price_service = PriceUpdateService()
            
            # Track results
            results = {
                'total': len(providers),
                'success': 0,
                'failed': 0,
                'skipped': 0,
                'details': []
            }
            
            # Sync each provider
            for i, provider in enumerate(providers, 1):
                logger.info(f"\n[{i}/{len(providers)}] Syncing {provider.display_name} ({provider.provider_type})...")
                
                try:
                    start_time = datetime.utcnow()
                    
                    # Run price sync
                    result = price_service.sync_provider_prices(provider.provider_type)
                    
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    
                    if result.get('success'):
                        results['success'] += 1
                        records = result.get('records_synced', 0)
                        logger.info(f"✅ {provider.display_name}: SUCCESS - {records} records synced in {duration:.1f}s")
                        
                        results['details'].append({
                            'provider': provider.display_name,
                            'status': 'success',
                            'records': records,
                            'duration': duration
                        })
                    else:
                        results['failed'] += 1
                        error = result.get('error', 'Unknown error')
                        logger.error(f"❌ {provider.display_name}: FAILED - {error}")
                        
                        results['details'].append({
                            'provider': provider.display_name,
                            'status': 'failed',
                            'error': error,
                            'duration': duration
                        })
                
                except Exception as e:
                    results['failed'] += 1
                    logger.error(f"❌ {provider.display_name}: EXCEPTION - {str(e)}", exc_info=True)
                    
                    results['details'].append({
                        'provider': provider.display_name,
                        'status': 'failed',
                        'error': str(e),
                        'duration': 0
                    })
            
            # Print summary
            logger.info("\n" + "=" * 80)
            logger.info("PRICE SYNC SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total providers: {results['total']}")
            logger.info(f"✅ Successful:   {results['success']}")
            logger.info(f"❌ Failed:       {results['failed']}")
            logger.info(f"⏭️  Skipped:      {results['skipped']}")
            
            total_records = sum(d.get('records', 0) for d in results['details'] if d['status'] == 'success')
            total_duration = sum(d.get('duration', 0) for d in results['details'])
            
            logger.info(f"\nTotal records synced: {total_records}")
            logger.info(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
            
            logger.info("\nDetails:")
            for detail in results['details']:
                if detail['status'] == 'success':
                    logger.info(f"  ✅ {detail['provider']}: {detail['records']} records in {detail['duration']:.1f}s")
                else:
                    logger.info(f"  ❌ {detail['provider']}: {detail.get('error', 'Unknown error')}")
            
            logger.info("=" * 80)
            
            # Return exit code (0 = success, 1 = some failures, 2 = all failed)
            if results['failed'] == 0:
                return 0
            elif results['success'] > 0:
                return 1
            else:
                return 2
            
        except Exception as e:
            logger.error(f"Fatal error in price sync: {str(e)}", exc_info=True)
            return 2


def sync_single_provider(provider_type: str):
    """Sync pricing data for a single provider"""
    app = create_app()
    
    with app.app_context():
        try:
            logger.info(f"Starting price sync for provider: {provider_type}")
            
            # Check if provider exists and is enabled
            provider = ProviderCatalog.query.filter_by(provider_type=provider_type).first()
            
            if not provider:
                logger.error(f"Provider '{provider_type}' not found in catalog")
                return 2
            
            if not provider.is_enabled:
                logger.warning(f"Provider '{provider_type}' is disabled")
                return 1
            
            if not provider.has_pricing_api:
                logger.warning(f"Provider '{provider_type}' does not have pricing API")
                return 1
            
            # Run price sync
            price_service = PriceUpdateService()
            start_time = datetime.utcnow()
            
            result = price_service.sync_provider_prices(provider_type)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            if result.get('success'):
                records = result.get('records_synced', 0)
                logger.info(f"✅ SUCCESS: {records} records synced in {duration:.1f}s")
                return 0
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ FAILED: {error}")
                return 1
            
        except Exception as e:
            logger.error(f"Exception during sync: {str(e)}", exc_info=True)
            return 2


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Sync pricing data from cloud providers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync all providers
  python scripts/sync_provider_prices.py
  
  # Sync specific provider
  python scripts/sync_provider_prices.py --provider yandex
  
  # Sync specific provider (short form)
  python scripts/sync_provider_prices.py -p selectel

Cron examples:
  # Daily at 2 AM
  0 2 * * * cd /path/to/InfraZen && ./venv/bin/python scripts/sync_provider_prices.py >> logs/cron_price_sync.log 2>&1
  
  # Every 6 hours
  0 */6 * * * cd /path/to/InfraZen && ./venv/bin/python scripts/sync_provider_prices.py >> logs/cron_price_sync.log 2>&1
  
  # Specific provider daily at 3 AM
  0 3 * * * cd /path/to/InfraZen && ./venv/bin/python scripts/sync_provider_prices.py -p yandex >> logs/cron_yandex_sync.log 2>&1
        """
    )
    
    parser.add_argument(
        '-p', '--provider',
        type=str,
        help='Sync only this provider (e.g., yandex, selectel, beget)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Run sync
    if args.provider:
        exit_code = sync_single_provider(args.provider)
    else:
        exit_code = sync_all_providers()
    
    sys.exit(exit_code)

