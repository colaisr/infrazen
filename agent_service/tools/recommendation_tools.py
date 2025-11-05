"""
Read-only tools for recommendation chat agent.
Tools provide access to recommendation, resource, and pricing data.
"""

import logging
import json
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class RecommendationTools:
    """Read-only tools for accessing recommendation data."""
    
    def __init__(self, flask_app):
        """
        Initialize tools with Flask app context.
        
        Args:
            flask_app: Flask application instance for database access
        """
        self.flask_app = flask_app
        
    def get_recommendation_details(self, rec_id: int) -> Dict:
        """
        Получить полные детали рекомендации по оптимизации.
        
        Используй этот инструмент, когда пользователь спрашивает о деталях текущей рекомендации,
        экономии, провайдерах, ресурсах или любых других аспектах рекомендации.
        
        Отвечай пользователю на русском языке, используя данные из этого инструмента.
        
        Args:
            rec_id: ID рекомендации
            
        Returns:
            Словарь с деталями рекомендации:
            - id, title, type, severity, status
            - estimated_monthly_savings (₽/мес)
            - target_provider, target_sku
            - resource (связанный ресурс)
            - insights, metrics (дополнительные данные)
        """
        try:
            with self.flask_app.app_context():
                from app.core.models import OptimizationRecommendation, Resource
                
                rec = OptimizationRecommendation.query.filter_by(id=rec_id).first()
                
                if not rec:
                    return {'error': f'Рекомендация с ID {rec_id} не найдена'}
                
                # Get related resource
                resource_data = None
                if rec.resource_id:
                    resource = Resource.query.filter_by(id=rec.resource_id).first()
                    if resource:
                        resource_data = {
                            'id': resource.id,
                            'name': resource.name,
                            'type': resource.resource_type,
                            'provider': resource.provider.name if resource.provider else None,
                            'effective_cost': float(resource.effective_cost) if resource.effective_cost else 0,
                            'status': resource.status,
                            'region': resource.region
                        }
                
                # Parse insights and metrics
                insights = {}
                if rec.insights:
                    try:
                        insights = json.loads(rec.insights) if isinstance(rec.insights, str) else rec.insights
                    except:
                        pass
                        
                metrics = {}
                if rec.metrics:
                    try:
                        metrics = json.loads(rec.metrics) if isinstance(rec.metrics, str) else rec.metrics
                    except:
                        pass
                
                return {
                    'id': rec.id,
                    'title': rec.title,
                    'type': rec.type,
                    'severity': rec.severity,
                    'status': rec.status,
                    'estimated_monthly_savings': float(rec.estimated_monthly_savings) if rec.estimated_monthly_savings else 0,
                    'target_provider': rec.target_provider,
                    'target_sku': rec.target_sku,
                    'description': rec.description,
                    'resource': resource_data,
                    'insights': insights,
                    'metrics': metrics,
                    'created_at': rec.created_at.isoformat() if rec.created_at else None
                }
                
        except Exception as e:
            logger.error(f"Error getting recommendation details: {e}", exc_info=True)
            return {'error': f'Ошибка при получении данных: {str(e)}'}
    
    def get_resource_details(self, resource_id: int) -> Dict:
        """
        Получить детальную информацию о ресурсе (сервер, диск, IP и т.д.).
        
        Используй этот инструмент, когда нужно узнать подробности о конкретном ресурсе:
        характеристики, конфигурацию, стоимость, провайдера, регион.
        
        Отвечай пользователю на русском языке.
        
        Args:
            resource_id: ID ресурса
            
        Returns:
            Словарь с деталями ресурса:
            - id, name, type, status
            - provider, region
            - effective_cost (₽/мес)
            - provider_config (CPU, RAM, Storage и др.)
            - tags
        """
        try:
            with self.flask_app.app_context():
                from app.core.models import Resource
                
                resource = Resource.query.filter_by(id=resource_id).first()
                
                if not resource:
                    return {'error': f'Ресурс с ID {resource_id} не найден'}
                
                # Parse provider_config
                config = {}
                if resource.provider_config:
                    try:
                        config = json.loads(resource.provider_config) if isinstance(resource.provider_config, str) else resource.provider_config
                    except:
                        pass
                
                # Extract key specs
                cpu_cores = config.get('vcpus') or config.get('cores')
                ram_gb = config.get('ram_gb')
                storage_gb = config.get('total_storage_gb') or config.get('storage_gb')
                
                # Parse tags
                tags = {}
                if resource.tags:
                    try:
                        tags = json.loads(resource.tags) if isinstance(resource.tags, str) else resource.tags
                    except:
                        pass
                
                return {
                    'id': resource.id,
                    'name': resource.name,
                    'type': resource.resource_type,
                    'status': resource.status,
                    'provider': resource.provider.name if resource.provider else None,
                    'provider_id': resource.provider_id,
                    'region': resource.region,
                    'effective_cost': float(resource.effective_cost) if resource.effective_cost else 0,
                    'config': config,
                    'specs': {
                        'cpu_cores': cpu_cores,
                        'ram_gb': ram_gb,
                        'storage_gb': storage_gb
                    },
                    'tags': tags,
                    'created_at': resource.created_at.isoformat() if resource.created_at else None
                }
                
        except Exception as e:
            logger.error(f"Error getting resource details: {e}", exc_info=True)
            return {'error': f'Ошибка при получении данных: {str(e)}'}
    
    def get_provider_pricing(self, provider: str, resource_type: str) -> List[Dict]:
        """
        Получить актуальные цены провайдера для определённого типа ресурса.
        
        Используй этот инструмент для сравнения цен между провайдерами или поиска
        альтернативных конфигураций с лучшей ценой.
        
        Отвечай пользователю на русском языке.
        
        Args:
            provider: Название провайдера (beget, selectel, yandex)
            resource_type: Тип ресурса (server, vm, storage, snapshot и т.д.)
            
        Returns:
            Список SKU с ценами (топ 10 по возрастанию цены):
            - sku, name, description
            - monthly_price (₽/мес)
            - specs (CPU, RAM, Storage)
            - region
        """
        try:
            with self.flask_app.app_context():
                from app.core.models import ProviderPrice
                
                prices = ProviderPrice.query.filter_by(
                    provider=provider.lower(),
                    resource_type=resource_type.lower()
                ).order_by(ProviderPrice.monthly_price.asc()).limit(10).all()
                
                if not prices:
                    return []
                
                result = []
                for price in prices:
                    # Parse specs
                    specs = {}
                    if price.specs:
                        try:
                            specs = json.loads(price.specs) if isinstance(price.specs, str) else price.specs
                        except:
                            pass
                    
                    result.append({
                        'sku': price.sku,
                        'name': price.name,
                        'description': price.description,
                        'monthly_price': float(price.monthly_price) if price.monthly_price else 0,
                        'specs': specs,
                        'region': price.region,
                        'currency': price.currency
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting provider pricing: {e}", exc_info=True)
            return []
    
    def calculate_savings(
        self, 
        current_cost: float, 
        new_cost: float, 
        period: str = "month"
    ) -> Dict:
        """
        Рассчитать экономию при переходе на новую конфигурацию или провайдера.
        
        Используй этот инструмент для точного расчёта экономии в разных периодах
        и процентах. Помогает пользователю понять выгоду от изменений.
        
        Отвечай пользователю на русском языке, форматируй суммы с разделителями тысяч.
        
        Args:
            current_cost: Текущая стоимость (₽/мес)
            new_cost: Новая стоимость (₽/мес)
            period: Период расчёта (month, quarter, year)
            
        Returns:
            Словарь с расчётами:
            - monthly_savings (₽/мес)
            - period_savings (за выбранный период)
            - yearly_savings (₽/год)
            - savings_percent (%)
            - roi_months (окупаемость в месяцах, если есть затраты на миграцию)
        """
        try:
            monthly_savings = current_cost - new_cost
            
            period_multipliers = {
                'month': 1,
                'quarter': 3,
                'year': 12
            }
            
            multiplier = period_multipliers.get(period.lower(), 1)
            period_savings = monthly_savings * multiplier
            yearly_savings = monthly_savings * 12
            
            savings_percent = 0
            if current_cost > 0:
                savings_percent = (monthly_savings / current_cost) * 100
            
            return {
                'monthly_savings': round(monthly_savings, 2),
                'period_savings': round(period_savings, 2),
                'period': period,
                'yearly_savings': round(yearly_savings, 2),
                'savings_percent': round(savings_percent, 2),
                'current_cost': current_cost,
                'new_cost': new_cost,
                'is_saving': monthly_savings > 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating savings: {e}", exc_info=True)
            return {'error': f'Ошибка расчёта: {str(e)}'}
    
    def get_migration_risks(
        self, 
        resource_id: int, 
        target_provider: str
    ) -> Dict:
        """
        Оценить риски и сложность миграции ресурса на другого провайдера.
        
        Используй этот инструмент, когда пользователь спрашивает о рисках миграции,
        сложности переноса, downtime или совместимости.
        
        Отвечай пользователю на русском языке, будь конкретным и честным о рисках.
        
        Args:
            resource_id: ID ресурса для миграции
            target_provider: Целевой провайдер (beget, selectel, yandex)
            
        Returns:
            Словарь с оценкой рисков:
            - risk_level (low, medium, high)
            - estimated_downtime_minutes
            - complexity (simple, moderate, complex)
            - risks (список рисков)
            - migration_steps (основные шаги)
            - recommendations (рекомендации)
        """
        try:
            with self.flask_app.app_context():
                from app.core.models import Resource
                
                resource = Resource.query.filter_by(id=resource_id).first()
                
                if not resource:
                    return {'error': f'Ресурс с ID {resource_id} не найден'}
                
                current_provider = resource.provider.name if resource.provider else 'unknown'
                resource_type = resource.resource_type
                
                # Base risk assessment
                risk_level = 'medium'
                downtime = 30  # minutes
                complexity = 'moderate'
                
                # Adjust based on resource type
                if resource_type in ['snapshot', 'volume']:
                    downtime = 15
                    complexity = 'simple'
                    risk_level = 'low'
                elif resource_type in ['server', 'vm', 'instance']:
                    downtime = 30
                    complexity = 'moderate'
                    risk_level = 'medium'
                elif resource_type in ['database', 'cluster']:
                    downtime = 60
                    complexity = 'complex'
                    risk_level = 'high'
                
                # Common risks
                risks = [
                    'Downtime во время миграции',
                    'Необходимость переконфигурации DNS',
                    'Возможная потеря данных без бэкапа',
                    'Различия в API/интерфейсах провайдеров',
                    'Несовместимость некоторых функций'
                ]
                
                # Migration steps
                steps = [
                    '1. Создать снапшот/бэкап текущего ресурса',
                    f'2. Развернуть новый ресурс на {target_provider}',
                    '3. Настроить конфигурацию и окружение',
                    '4. Перенести данные',
                    '5. Протестировать работу',
                    '6. Переключить DNS/трафик',
                    '7. Мониторинг 24-48 часов'
                ]
                
                # Recommendations
                recommendations = [
                    'Выполнять миграцию в нерабочее время',
                    'Обязательно сделать полный бэкап перед началом',
                    'Протестировать на тестовом окружении',
                    'Подготовить план отката (rollback)',
                    'Держать старый ресурс активным 1-2 недели для страховки'
                ]
                
                return {
                    'resource_name': resource.name,
                    'resource_type': resource_type,
                    'current_provider': current_provider,
                    'target_provider': target_provider,
                    'risk_level': risk_level,
                    'estimated_downtime_minutes': downtime,
                    'complexity': complexity,
                    'risks': risks,
                    'migration_steps': steps,
                    'recommendations': recommendations
                }
                
        except Exception as e:
            logger.error(f"Error assessing migration risks: {e}", exc_info=True)
            return {'error': f'Ошибка оценки рисков: {str(e)}'}

