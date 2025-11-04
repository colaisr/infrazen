"""
Data access tools for Agent Service
Read-only access to InfraZen database via SQLAlchemy
"""
import json
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DataAccessTools:
    """Read-only tools to access InfraZen data"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_recommendation(self, recommendation_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch recommendation details with related resource and provider info
        
        Args:
            recommendation_id: Recommendation ID
            
        Returns:
            Dict with recommendation, resource, provider, and pricing data
        """
        from app.core.models.recommendations import OptimizationRecommendation
        from app.core.models.resource import Resource
        from app.core.models.provider import CloudProvider
        
        try:
            rec = self.db.query(OptimizationRecommendation).filter_by(id=recommendation_id).first()
            if not rec:
                logger.warning(f"Recommendation {recommendation_id} not found")
                return None
            
            # Get related resource
            resource = self.db.query(Resource).filter_by(id=rec.resource_id).first() if rec.resource_id else None
            
            # Get current provider
            current_provider = self.db.query(CloudProvider).filter_by(id=rec.provider_id).first() if rec.provider_id else None
            
            # Parse insights and metrics (stored as Python dict strings)
            insights = None
            metrics = None
            try:
                if rec.insights:
                    # Try JSON first, then eval (for Python dict format with single quotes)
                    try:
                        insights = json.loads(rec.insights)
                    except json.JSONDecodeError:
                        # Handle Python dict format (single quotes)
                        import ast
                        insights = ast.literal_eval(rec.insights)
            except Exception as e:
                logger.warning(f"Could not parse insights: {e}, raw: {rec.insights[:100]}")
            
            try:
                if rec.metrics_snapshot:
                    try:
                        metrics = json.loads(rec.metrics_snapshot)
                    except json.JSONDecodeError:
                        import ast
                        metrics = ast.literal_eval(rec.metrics_snapshot)
            except Exception as e:
                logger.warning(f"Could not parse metrics: {e}, raw: {rec.metrics_snapshot[:100]}")
            
            result = {
                'recommendation': {
                    'id': rec.id,
                    'type': rec.recommendation_type,
                    'category': rec.category,
                    'severity': rec.severity,
                    'title': rec.title,
                    'description': rec.description,
                    'target_provider': rec.target_provider,
                    'target_sku': rec.target_sku,
                    'target_region': rec.target_region,
                    'estimated_monthly_savings': float(rec.estimated_monthly_savings or 0),
                    'currency': rec.currency,
                    'confidence_score': float(rec.confidence_score or 0),
                    'insights': insights,
                    'metrics': metrics
                },
                'resource': None,
                'current_provider': None
            }
            
            # Add resource details
            if resource:
                # Parse tags for specs
                tags = {}
                if resource.tags:
                    for tag in resource.tags:
                        tags[tag.tag_key] = tag.tag_value
                
                result['resource'] = {
                    'id': resource.id,
                    'name': resource.resource_name,
                    'resource_type': resource.resource_type,
                    'status': resource.status,
                    'region': resource.region,
                    'monthly_cost': float(resource.effective_cost or resource.list_price or 0),
                    'daily_cost': float(resource.daily_cost or 0),
                    'cpu_cores': tags.get('cpu_cores'),
                    'ram_gb': tags.get('ram_gb'),
                    'storage_gb': tags.get('storage_gb'),
                    'storage_type': tags.get('storage_type'),
                    'tags': tags
                }
            
            # Add current provider details
            if current_provider:
                result['current_provider'] = {
                    'id': current_provider.id,
                    'provider_type': current_provider.provider_type,
                    'connection_name': current_provider.connection_name,
                    'account_id': current_provider.account_id
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching recommendation {recommendation_id}: {e}", exc_info=True)
            return None
    
    def get_alternative_prices(
        self, 
        provider: str, 
        sku: str, 
        region: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch price details for a specific SKU
        
        Args:
            provider: Provider name (e.g., 'selectel', 'beget')
            sku: SKU identifier
            region: Optional region filter
            
        Returns:
            Dict with price details
        """
        from app.core.models.pricing import ProviderPrice
        
        try:
            query = self.db.query(ProviderPrice).filter_by(
                provider=provider,
                provider_sku=sku
            )
            
            if region:
                query = query.filter_by(region=region)
            
            price = query.first()
            if not price:
                logger.warning(f"Price not found: {provider}/{sku}/{region}")
                return None
            
            return {
                'id': price.id,
                'provider': price.provider,
                'sku': price.provider_sku,
                'region': price.region,
                'resource_type': price.resource_type,
                'cpu_cores': price.cpu_cores,
                'ram_gb': price.ram_gb,
                'storage_gb': price.storage_gb,
                'storage_type': price.storage_type,
                'monthly_cost': float(price.monthly_cost or 0),
                'currency': price.currency,
                'last_updated': price.last_updated.isoformat() if price.last_updated else None
            }
            
        except Exception as e:
            logger.error(f"Error fetching price {provider}/{sku}: {e}", exc_info=True)
            return None

