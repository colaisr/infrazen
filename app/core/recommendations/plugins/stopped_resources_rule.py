from __future__ import annotations

from typing import List
from datetime import datetime, timedelta
from ..interfaces import BaseRule, RuleScope, RuleCategory, RecommendationOutput


class StoppedResourceCleanupRule(BaseRule):
    """
    Рекомендует удалить серверы/VM, которые остановлены длительное время.
    
    Логика:
    - Проверяет статус ресурса (STOPPED, DEALLOCATED, TERMINATED)
    - Для остановленных ресурсов рекомендует удаление для экономии
    - Учитывает только затраты на хранение (storage), т.к. compute и RAM не оплачиваются
    """
    
    @property
    def id(self) -> str:
        return "cost.cleanup.stopped_resources"

    @property
    def name(self) -> str:
        return "Оптимизация: удаление остановленных ресурсов"

    @property
    def description(self) -> str:
        return (
            "Рекомендует удалить серверы и виртуальные машины, которые остановлены. "
            "Остановленные ресурсы продолжают тарифицироваться за хранилище (диски), "
            "но не используются. Удаление освобождает ресурсы и экономит средства на хранении данных."
        )

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.COST

    @property
    def scope(self) -> RuleScope:
        return RuleScope.RESOURCE

    @property
    def resource_types(self):
        return {"server", "vm"}

    def applies(self, resource, context) -> bool:
        """Применяется только к серверам/VM."""
        try:
            rtype = getattr(resource, 'resource_type', None) or getattr(resource, 'type', None)
        except Exception:
            rtype = None
        if rtype is None:
            return False
        rtype = str(rtype).lower()
        return rtype in {"server", "vm"}

    def evaluate(self, resource, context) -> List[RecommendationOutput]:
        """
        Проверяет, остановлен ли ресурс, и рекомендует удаление.
        """
        # Проверяем статус ресурса
        try:
            status = getattr(resource, 'status', '').upper()
        except Exception:
            status = ''
        
        # Только для остановленных ресурсов
        if status not in ('STOPPED', 'DEALLOCATED', 'TERMINATED'):
            return []
        
        # Пропускаем ресурсы Kubernetes (они управляются кластером)
        try:
            tags = {t.tag_key: t.tag_value for t in getattr(resource, 'tags', [])}
            resource_name = getattr(resource, 'resource_name', '') or ''
            
            if tags.get('is_kubernetes_node') == 'true' or tags.get('is_kubernetes_node') is True:
                return []
            
            if resource_name.startswith('k8s-csi-'):
                return []
            
            if tags.get('kubernetes_cluster_id'):
                return []
        except Exception:
            pass
        
        # Получаем текущие затраты (только storage для остановленного ресурса)
        current_monthly = 0.0
        try:
            if getattr(resource, 'effective_cost', 0) and getattr(resource, 'billing_period', '') == 'monthly':
                current_monthly = float(resource.effective_cost or 0.0)
            elif getattr(resource, 'daily_cost', 0):
                current_monthly = float(resource.daily_cost or 0.0) * 30.0
        except Exception:
            current_monthly = 0.0
        
        # Если затраты нулевые или очень малые, не создаём рекомендацию
        if current_monthly < 10.0:
            return []
        
        # Получаем имя ресурса для отображения
        resource_name = getattr(resource, 'resource_name', None) or getattr(resource, 'name', 'неизвестно')
        
        # Формируем рекомендацию
        title = "Удалить остановленный сервер"
        
        if status == 'STOPPED':
            status_text = "остановлен"
        elif status == 'DEALLOCATED':
            status_text = "деаллоцирован"
        elif status == 'TERMINATED':
            status_text = "завершён"
        else:
            status_text = "не запущен"
        
        desc = (
            f"Сервер '{resource_name}' {status_text} и продолжает тарифицироваться за хранилище (~{current_monthly:.2f} RUB/мес). "
            f"Если сервер больше не нужен, рекомендуется удалить его для экономии средств. "
            f"Перед удалением убедитесь, что важные данные сохранены."
        )
        
        return [
            RecommendationOutput(
                recommendation_type="cleanup_stopped",
                title=title,
                description=desc,
                category=RuleCategory.COST,
                severity="medium",
                source=self.id,
                estimated_monthly_savings=current_monthly,
                currency=getattr(resource, 'currency', 'RUB') or 'RUB',
                confidence_score=0.8,
                metrics_snapshot={
                    "status": status,
                    "storage_cost_monthly": current_monthly
                },
                insights={
                    "action": "delete",
                    "reason": "stopped_unused",
                    "storage_only_cost": True
                },
            )
        ]


RULES = [StoppedResourceCleanupRule]



