"""
Analytics Service - Data operations for analytics dashboard
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import desc, func, and_

from app.core.database import db
from app.core.models.complete_sync import CompleteSync
from app.core.models.sync import SyncSnapshot
from app.core.models.resource import Resource
from app.core.models.recommendations import OptimizationRecommendation
from app.core.models.provider import CloudProvider


class AnalyticsService:
    """Service for analytics data operations"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def get_executive_summary(self) -> Dict[str, Any]:
        """Get executive summary KPIs"""
        # Get latest complete sync
        latest_sync = CompleteSync.query.filter_by(user_id=self.user_id)\
            .order_by(desc(CompleteSync.sync_completed_at)).first()
        
        # Get active resources count
        active_resources = Resource.query.filter_by(is_active=True).count()
        
        # Get implemented recommendations
        implemented_recs = OptimizationRecommendation.query.filter_by(status='implemented').all()
        total_savings = sum(rec.estimated_monthly_savings or 0 for rec in implemented_recs)
        
        # Get provider success rate
        if latest_sync:
            provider_success_rate = (latest_sync.successful_providers / latest_sync.total_providers_synced * 100) if latest_sync.total_providers_synced > 0 else 0
        else:
            provider_success_rate = 0
        
        return {
            'total_daily_cost': latest_sync.total_daily_cost if latest_sync else 0,
            'total_monthly_cost': latest_sync.total_monthly_cost if latest_sync else 0,
            'active_resources': active_resources,
            'provider_success_rate': provider_success_rate,
            'total_savings': total_savings,
            'implemented_recommendations_count': len(implemented_recs),
            'last_sync_date': latest_sync.sync_completed_at if latest_sync else None
        }
    
    def get_main_spending_trends(self, days: int = 30, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get main spending trends for the primary chart"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get complete syncs within date range
        syncs = CompleteSync.query.filter(
            and_(
                CompleteSync.user_id == self.user_id,
                CompleteSync.sync_completed_at >= start_date,
                CompleteSync.sync_completed_at <= end_date,
                CompleteSync.sync_status == 'success'
            )
        ).order_by(CompleteSync.sync_completed_at).all()
        
        trends = []
        for sync in syncs:
            trend_data = {
                'date': sync.sync_completed_at.strftime('%Y-%m-%d'),
                'total_cost': float(sync.total_daily_cost or 0),
                'total_resources': sync.total_resources_found or 0,
                'successful_providers': sync.successful_providers or 0
            }
            
            # Add provider-specific data if cost_by_provider exists
            if sync.cost_by_provider:
                try:
                    import json
                    cost_by_provider = json.loads(sync.cost_by_provider) if isinstance(sync.cost_by_provider, str) else sync.cost_by_provider
                    trend_data['cost_by_provider'] = cost_by_provider
                except (json.JSONDecodeError, TypeError):
                    trend_data['cost_by_provider'] = {}
            else:
                trend_data['cost_by_provider'] = {}
            
            trends.append(trend_data)
        
        return trends
    
    def get_service_analysis(self) -> Dict[str, Any]:
        """Get service-level cost breakdown"""
        # Get latest complete sync
        latest_sync = CompleteSync.query.filter_by(user_id=self.user_id)\
            .order_by(desc(CompleteSync.sync_completed_at)).first()
        
        if not latest_sync:
            return {'services': [], 'total_cost': 0}
        
        # Get resources from latest sync
        # We'll use active resources as proxy for latest sync data
        resources = Resource.query.filter_by(is_active=True).all()
        
        service_breakdown = {}
        total_cost = 0
        
        for resource in resources:
            service = resource.service_name or 'Unknown Service'
            daily_cost = resource.daily_cost or 0
            
            if service not in service_breakdown:
                service_breakdown[service] = {
                    'cost': 0,
                    'count': 0,
                    'resources': []
                }
            
            service_breakdown[service]['cost'] += daily_cost
            service_breakdown[service]['count'] += 1
            service_breakdown[service]['resources'].append({
                'name': resource.resource_name,
                'cost': daily_cost,
                'type': resource.resource_type
            })
            total_cost += daily_cost
        
        # Convert to list and sort by cost
        services = []
        for service, data in service_breakdown.items():
            services.append({
                'name': service,
                'cost': data['cost'],
                'count': data['count'],
                'percentage': (data['cost'] / total_cost * 100) if total_cost > 0 else 0,
                'resources': data['resources']
            })
        
        services.sort(key=lambda x: x['cost'], reverse=True)
        
        return {
            'services': services,
            'total_cost': total_cost,
            'total_resources': len(resources)
        }
    
    def get_provider_breakdown(self) -> Dict[str, Any]:
        """Get provider cost breakdown for pie chart"""
        # Get latest complete sync
        latest_sync = CompleteSync.query.filter_by(user_id=self.user_id)\
            .order_by(desc(CompleteSync.sync_completed_at)).first()
        
        if not latest_sync or not latest_sync.cost_by_provider:
            return {'providers': [], 'total_cost': 0}
        
        try:
            import json
            cost_by_provider = json.loads(latest_sync.cost_by_provider) if isinstance(latest_sync.cost_by_provider, str) else latest_sync.cost_by_provider
            
            # Get provider names - handle string keys
            provider_ids = list(cost_by_provider.keys())
            providers = CloudProvider.query.filter(CloudProvider.id.in_(provider_ids)).all()
            provider_names = {p.id: p.connection_name for p in providers}
            
            total_cost = sum(cost_by_provider.values())
            
            provider_data = []
            for provider_id, cost in cost_by_provider.items():
                provider_data.append({
                    'id': provider_id,
                    'name': provider_names.get(provider_id, f'Provider {provider_id}'),
                    'cost': float(cost),
                    'percentage': (cost / total_cost * 100) if total_cost > 0 else 0
                })
            
            provider_data.sort(key=lambda x: x['cost'], reverse=True)
            
            return {
                'providers': provider_data,
                'total_cost': total_cost
            }
            
        except (json.JSONDecodeError, TypeError, ValueError):
            return {'providers': [], 'total_cost': 0}
    
    def get_provider_trends(self, provider_id: Optional[int] = None, days: int = 30) -> List[Dict[str, Any]]:
        """Get individual provider spending trends"""
        from app.core.models.provider import CloudProvider
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get sync snapshots for the provider, filtered by user
        query = SyncSnapshot.query.join(CloudProvider).filter(
            and_(
                CloudProvider.user_id == self.user_id,
                SyncSnapshot.sync_completed_at >= start_date,
                SyncSnapshot.sync_completed_at <= end_date,
                SyncSnapshot.sync_status == 'success'
            )
        )
        
        if provider_id:
            query = query.filter(SyncSnapshot.provider_id == provider_id)
        
        snapshots = query.order_by(SyncSnapshot.sync_completed_at).all()
        
        trends = []
        for snapshot in snapshots:
            # Get provider name
            provider = CloudProvider.query.get(snapshot.provider_id)
            provider_name = provider.connection_name if provider else f'Provider {snapshot.provider_id}'
            
            trends.append({
                'date': snapshot.sync_completed_at.strftime('%Y-%m-%d'),
                'provider_id': snapshot.provider_id,
                'provider_name': provider_name,
                'total_cost': float(snapshot.total_monthly_cost or 0),
                'resources_found': snapshot.total_resources_found or 0
            })
        
        return trends
    
    def get_implemented_recommendations(self) -> List[Dict[str, Any]]:
        """Get implemented recommendations with savings"""
        recommendations = OptimizationRecommendation.query.filter_by(status='implemented').all()
        
        rec_data = []
        for rec in recommendations:
            rec_data.append({
                'id': rec.id,
                'title': rec.title,
                'description': rec.description,
                'recommendation_type': rec.recommendation_type,
                'monthly_savings': float(rec.estimated_monthly_savings or 0),
                'one_time_savings': float(rec.estimated_one_time_savings or 0),
                'applied_at': rec.applied_at.isoformat() if rec.applied_at else None,
                'resource_name': rec.resource_name,
                'resource_type': rec.resource_type
            })
        
        return rec_data
    
    def get_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """Get pending optimization opportunities"""
        recommendations = OptimizationRecommendation.query.filter_by(status='pending').all()
        
        opp_data = []
        for rec in recommendations:
            opp_data.append({
                'id': rec.id,
                'title': rec.title,
                'description': rec.description,
                'recommendation_type': rec.recommendation_type,
                'severity': rec.severity,
                'potential_savings': float(rec.estimated_monthly_savings or 0),
                'confidence_score': float(rec.confidence_score or 0),
                'resource_name': rec.resource_name,
                'resource_type': rec.resource_type
            })
        
        return opp_data
    
    def export_analytics_report(self, format: str = 'pdf') -> bytes:
        """Export analytics report in specified format"""
        # This would be implemented with report generation libraries
        # For now, return a placeholder
        if format == 'pdf':
            return b'PDF report placeholder'
        elif format == 'excel':
            return b'Excel report placeholder'
        elif format == 'csv':
            return b'CSV report placeholder'
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_chart_data_for_main_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get formatted data for main spending chart"""
        trends = self.get_main_spending_trends(days)
        
        if not trends:
            return {
                'labels': [],
                'datasets': []
            }
        
        # Extract labels (dates)
        labels = [trend['date'] for trend in trends]
        
        # Create datasets
        datasets = []
        
        # Total aggregated line
        total_costs = [trend['total_cost'] for trend in trends]
        datasets.append({
            'label': 'Общие расходы',
            'data': total_costs,
            'borderColor': '#1e40af',
            'backgroundColor': 'rgba(30, 64, 175, 0.1)',
            'tension': 0.4,
            'fill': True
        })
        
        # Provider-specific lines
        provider_colors = ['#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#8b5cf6']
        color_index = 0
        
        for trend in trends:
            if 'cost_by_provider' in trend and trend['cost_by_provider']:
                for provider_id, cost in trend['cost_by_provider'].items():
                    # Get provider name
                    provider = CloudProvider.query.get(int(provider_id))
                    provider_name = provider.connection_name if provider else f'Provider {provider_id}'
                    
                    # Check if we already have this provider in datasets
                    existing_dataset = None
                    for dataset in datasets:
                        if dataset['label'] == provider_name:
                            existing_dataset = dataset
                            break
                    
                    if existing_dataset:
                        # Add cost to existing provider dataset
                        existing_dataset['data'].append(float(cost))
                    else:
                        # Create new provider dataset
                        datasets.append({
                            'label': provider_name,
                            'data': [float(cost)],
                            'borderColor': provider_colors[color_index % len(provider_colors)],
                            'backgroundColor': f'rgba({provider_colors[color_index % len(provider_colors)].lstrip("#")}, 0.1)',
                            'tension': 0.4,
                            'fill': False
                        })
                        color_index += 1
        
        # Pad all datasets to same length
        max_length = len(labels)
        for dataset in datasets:
            while len(dataset['data']) < max_length:
                dataset['data'].append(0)
        
        return {
            'labels': labels,
            'datasets': datasets
        }
