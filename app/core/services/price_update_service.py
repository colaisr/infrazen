"""
Price Update Service - Handles scheduled and manual price updates
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.database import db
from app.core.services.pricing_service import PricingService
from app.core.models.provider_catalog import ProviderCatalog
from app.providers.plugin_system import ProviderPluginManager

logger = logging.getLogger(__name__)


class PriceUpdateService:
    """Service for updating pricing data from providers"""
    
    def __init__(self):
        self.pricing_service = PricingService()
        self.plugin_manager = ProviderPluginManager()
    
    def sync_provider_prices(self, provider_type: str) -> Dict[str, Any]:
        """
        Sync pricing data for a specific provider
        
        Args:
            provider_type: Provider type (e.g., 'beget', 'selectel')
            
        Returns:
            Dict: Result of the sync operation
        """
        try:
            logger.info(f"Starting price sync for provider: {provider_type}")
            
            # Update sync status to in_progress
            self.pricing_service.update_provider_sync_status(provider_type, 'in_progress')
            
            # Get provider plugin class
            plugin_class = self.plugin_manager.get_plugin_class(provider_type)
            if not plugin_class:
                error_msg = f"Provider plugin not found: {provider_type}"
                logger.error(error_msg)
                self.pricing_service.update_provider_sync_status(provider_type, 'failed', error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'provider': provider_type
                }
            
            # Get pricing data from provider
            try:
                # Create plugin instance (we need credentials, but for pricing we can use empty)
                plugin_instance = plugin_class(0, {}, {})
                pricing_data = plugin_instance.get_pricing_data()
                if not pricing_data:
                    error_msg = f"No pricing data returned from {provider_type}"
                    logger.warning(error_msg)
                    self.pricing_service.update_provider_sync_status(provider_type, 'failed', error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'provider': provider_type
                    }
                
                logger.info(f"Retrieved {len(pricing_data)} pricing records from {provider_type}")
                
                # Save pricing data
                saved_records = self.pricing_service.bulk_save_price_data(pricing_data)
                
                # Update sync status to success
                self.pricing_service.update_provider_sync_status(provider_type, 'success')
                
                result = {
                    'success': True,
                    'message': f'Successfully synced {len(saved_records)} pricing records from {provider_type}',
                    'provider': provider_type,
                    'records_synced': len(saved_records),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                logger.info(f"Price sync completed successfully for {provider_type}: {len(saved_records)} records")
                return result
                
            except Exception as e:
                error_msg = f"Error retrieving pricing data from {provider_type}: {str(e)}"
                logger.error(error_msg)
                self.pricing_service.update_provider_sync_status(provider_type, 'failed', error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'provider': provider_type
                }
                
        except Exception as e:
            error_msg = f"Unexpected error during price sync for {provider_type}: {str(e)}"
            logger.error(error_msg)
            self.pricing_service.update_provider_sync_status(provider_type, 'failed', error_msg)
            return {
                'success': False,
                'error': error_msg,
                'provider': provider_type
            }
    
    def sync_all_enabled_providers(self) -> Dict[str, Any]:
        """
        Sync pricing data for all enabled providers
        
        Returns:
            Dict: Summary of sync operations
        """
        try:
            logger.info("Starting price sync for all enabled providers")
            
            # Get all enabled providers
            enabled_providers = ProviderCatalog.query.filter_by(is_enabled=True).all()
            
            if not enabled_providers:
                return {
                    'success': True,
                    'message': 'No enabled providers found',
                    'results': [],
                    'summary': {
                        'total_providers': 0,
                        'successful_syncs': 0,
                        'failed_syncs': 0
                    }
                }
            
            results = []
            successful_syncs = 0
            failed_syncs = 0
            
            for provider in enabled_providers:
                result = self.sync_provider_prices(provider.provider_type)
                results.append(result)
                
                if result['success']:
                    successful_syncs += 1
                else:
                    failed_syncs += 1
            
            summary = {
                'total_providers': len(enabled_providers),
                'successful_syncs': successful_syncs,
                'failed_syncs': failed_syncs,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Price sync completed for all providers: {summary}")
            
            return {
                'success': True,
                'message': f'Synced {successful_syncs}/{len(enabled_providers)} providers successfully',
                'results': results,
                'summary': summary
            }
            
        except Exception as e:
            error_msg = f"Error during bulk price sync: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'results': [],
                'summary': {
                    'total_providers': 0,
                    'successful_syncs': 0,
                    'failed_syncs': 0
                }
            }
    
    def get_sync_status(self, provider_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sync status for providers
        
        Args:
            provider_type: Optional provider type filter
            
        Returns:
            Dict: Sync status information
        """
        try:
            if provider_type:
                provider = ProviderCatalog.query.filter_by(provider_type=provider_type).first()
                if not provider:
                    return {
                        'success': False,
                        'error': f'Provider {provider_type} not found'
                    }
                
                return {
                    'success': True,
                    'provider': provider.to_dict()
                }
            else:
                providers = ProviderCatalog.query.all()
                return {
                    'success': True,
                    'providers': [provider.to_dict() for provider in providers]
                }
                
        except Exception as e:
            error_msg = f"Error getting sync status: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_pricing_statistics(self) -> Dict[str, Any]:
        """
        Get pricing system statistics
        
        Returns:
            Dict: Pricing statistics
        """
        try:
            return self.pricing_service.get_pricing_statistics()
        except Exception as e:
            logger.error(f"Error getting pricing statistics: {str(e)}")
            return {
                'error': str(e)
            }
