"""
Pricing Service - Handles price data management and updates
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from decimal import Decimal

from app.core.database import db
from app.core.models.pricing import ProviderPrice, PriceHistory, PriceComparisonRecommendation
from app.core.models.provider_catalog import ProviderCatalog

logger = logging.getLogger(__name__)


class PricingService:
    """Service for managing pricing data operations"""
    
    @staticmethod
    def save_price_data(price_data: Dict[str, Any]) -> ProviderPrice:
        """
        Save or update price data for a provider
        
        Args:
            price_data: Dictionary containing price information
            
        Returns:
            ProviderPrice: The saved or updated price record
        """
        try:
            # Check if price record already exists
            existing_price = ProviderPrice.query.filter_by(
                provider=price_data['provider'],
                resource_type=price_data['resource_type'],
                provider_sku=price_data.get('provider_sku'),
                region=price_data.get('region')
            ).first()
            
            old_monthly_cost = None
            if existing_price and existing_price.monthly_cost:
                old_monthly_cost = existing_price.monthly_cost
            
            if existing_price:
                # Update existing record
                for key, value in price_data.items():
                    if hasattr(existing_price, key):
                        setattr(existing_price, key, value)
                existing_price.last_updated = datetime.utcnow()
                price_record = existing_price
                logger.info(f"Updated price record for {price_data['provider']} {price_data['resource_type']}")
            else:
                # Create new record
                price_record = ProviderPrice(**price_data)
                db.session.add(price_record)
                logger.info(f"Created new price record for {price_data['provider']} {price_data['resource_type']}")
            
            # Track price change in history
            new_monthly_cost = price_data.get('monthly_cost')

            if old_monthly_cost is not None and new_monthly_cost is not None and old_monthly_cost != new_monthly_cost:
                old_val = float(old_monthly_cost)
                new_val = float(new_monthly_cost)
                change_percent = None
                if old_val:
                    change_percent = ((new_val - old_val) / old_val) * 100

                price_history = PriceHistory(
                    price_id=price_record.id,
                    old_monthly_cost=old_monthly_cost,
                    new_monthly_cost=new_monthly_cost,
                    change_percent=change_percent,
                    change_reason='price_update'
                )
                db.session.add(price_history)
                logger.info(f"Recorded price change: {old_monthly_cost} -> {price_data.get('monthly_cost')} ({change_percent}%)")
            
            db.session.commit()
            return price_record
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving price data: {str(e)}")
            raise
    
    @staticmethod
    def bulk_save_price_data(price_data_list: List[Dict[str, Any]]) -> List[ProviderPrice]:
        """
        Save multiple price records in batch. Existing records for the same provider
        (and optionally resource type/region) are removed before inserting the fresh
        dataset to ensure the table reflects only the latest snapshot.

        Args:
            price_data_list: List of price data dictionaries

        Returns:
            List[ProviderPrice]: List of saved price records
        """
        saved_records: List[ProviderPrice] = []

        if not price_data_list:
            logger.warning("bulk_save_price_data called with empty payload")
            return saved_records

        provider = price_data_list[0].get("provider")
        if not provider:
            raise ValueError("Pricing payload missing 'provider'")

        resource_type = price_data_list[0].get("resource_type")
        region = price_data_list[0].get("region")

        try:
            # Remove previous snapshot for this provider (optionally scoped by resource type/region)
            # We must delete dependent price_history rows first to satisfy FK constraints
            price_ids_subq = db.session.query(ProviderPrice.id).filter(ProviderPrice.provider == provider)
            if resource_type:
                price_ids_subq = price_ids_subq.filter(ProviderPrice.resource_type == resource_type)
            if region:
                price_ids_subq = price_ids_subq.filter(ProviderPrice.region == region)

            # Delete history records referencing the target prices
            history_deleted = db.session.query(PriceHistory).filter(PriceHistory.price_id.in_(price_ids_subq)).delete(synchronize_session=False)

            # Now delete the prices themselves
            deleted = db.session.query(ProviderPrice).filter(ProviderPrice.id.in_(price_ids_subq.subquery())).delete(synchronize_session=False)
            if deleted:
                logger.info(
                    "Removed %d price records and %d history rows for provider=%s resource_type=%s region=%s",
                    deleted,
                    history_deleted,
                    provider,
                    resource_type,
                    region,
                )

            for price_data in price_data_list:
                record = PricingService.save_price_data(price_data)
                saved_records.append(record)
            
            logger.info(f"Successfully saved {len(saved_records)} price records")
            return saved_records
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in bulk save: {str(e)}")
            raise
    
    @staticmethod
    def get_prices_by_provider(provider: str) -> List[ProviderPrice]:
        """
        Get all price records for a specific provider
        
        Args:
            provider: Provider name (e.g., 'beget', 'selectel')
            
        Returns:
            List[ProviderPrice]: List of price records
        """
        return ProviderPrice.query.filter_by(provider=provider).all()
    
    @staticmethod
    def get_prices_by_resource_type(resource_type: str) -> List[ProviderPrice]:
        """
        Get all price records for a specific resource type
        
        Args:
            resource_type: Resource type (e.g., 'server', 'volume')
            
        Returns:
            List[ProviderPrice]: List of price records
        """
        return ProviderPrice.query.filter_by(resource_type=resource_type).all()
    
    @staticmethod
    def find_similar_prices(target_specs: Dict[str, Any], 
                           min_score: float = 70.0,
                           max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Find similar price records based on specifications
        
        Args:
            target_specs: Target resource specifications
            min_score: Minimum similarity score (0-100)
            max_results: Maximum number of results to return
            
        Returns:
            List[Dict]: List of similar price records with similarity scores
        """
        try:
            # Get all price records that match basic criteria
            query = ProviderPrice.query
            
            # Filter by resource type if specified
            if target_specs.get('resource_type'):
                query = query.filter_by(resource_type=target_specs['resource_type'])
            
            # Filter by region if specified
            if target_specs.get('region'):
                query = query.filter_by(region=target_specs['region'])
            
            all_prices = query.all()
            
            # Calculate similarity scores
            similar_prices = []
            for price in all_prices:
                score = price.calculate_similarity_score(target_specs)
                if score >= min_score:
                    price_dict = price.to_dict()
                    price_dict['similarity_score'] = score
                    similar_prices.append(price_dict)
            
            # Sort by similarity score (highest first)
            similar_prices.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return similar_prices[:max_results]
            
        except Exception as e:
            logger.error(f"Error finding similar prices: {str(e)}")
            return []
    
    @staticmethod
    def update_provider_sync_status(provider_type: str, status: str, error_message: str = None):
        """
        Update provider sync status in catalog
        
        Args:
            provider_type: Provider type (e.g., 'beget', 'selectel')
            status: Sync status ('in_progress', 'success', 'failed')
            error_message: Error message if status is 'failed'
        """
        try:
            provider = ProviderCatalog.query.filter_by(provider_type=provider_type).first()
            if provider:
                provider.sync_status = status
                provider.sync_error = error_message
                
                if status == 'success':
                    provider.last_price_sync = datetime.utcnow()
                    provider.sync_error = None
                
                provider.updated_at = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"Updated sync status for {provider_type}: {status}")
            else:
                logger.warning(f"Provider {provider_type} not found in catalog")
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating provider sync status: {str(e)}")
            raise
    
    @staticmethod
    def get_price_history(provider: str, resource_type: str = None) -> List[PriceHistory]:
        """
        Get price history for a provider and optionally resource type
        
        Args:
            provider: Provider name
            resource_type: Optional resource type filter
            
        Returns:
            List[PriceHistory]: List of price history records
        """
        query = db.session.query(PriceHistory).join(ProviderPrice)
        query = query.filter(ProviderPrice.provider == provider)
        
        if resource_type:
            query = query.filter(ProviderPrice.resource_type == resource_type)
        
        return query.order_by(PriceHistory.change_date.desc()).all()
    
    @staticmethod
    def get_pricing_statistics() -> Dict[str, Any]:
        """
        Get pricing system statistics
        
        Returns:
            Dict: Statistics about the pricing system
        """
        try:
            total_prices = ProviderPrice.query.count()
            total_providers = ProviderCatalog.query.count()
            enabled_providers = ProviderCatalog.query.filter_by(is_enabled=True).count()
            
            # Count prices by provider
            provider_counts = {}
            for provider in ProviderCatalog.query.all():
                count = ProviderPrice.query.filter_by(provider=provider.provider_type).count()
                provider_counts[provider.provider_type] = count
            
            # Count recent price changes
            recent_changes = PriceHistory.query.filter(
                PriceHistory.change_date >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            ).count()
            
            return {
                'total_prices': total_prices,
                'total_providers': total_providers,
                'enabled_providers': enabled_providers,
                'provider_counts': provider_counts,
                'recent_price_changes': recent_changes,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting pricing statistics: {str(e)}")
            return {}
