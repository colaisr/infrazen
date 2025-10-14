"""
Seed sample optimization recommendations for testing the UI (10 items)
Run: python scripts/seed_recommendations.py
Idempotent: removes previous seed items by source/title before insert.
"""
from datetime import datetime, timedelta
import json

from app import create_app
from app.core.database import db
from app.core.models.recommendations import OptimizationRecommendation
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource


def pick_first(q):
    return q.first().id if q.first() else None


SAMPLES = [
    {
        'source': 'seed_rightsizing_cpu',
        'recommendation_type': 'rightsizing',
        'title': 'Снизить vCPU с 4 до 2 (низкая загрузка)',
        'description': 'Средняя загрузка CPU 6% за 14 дней. Рекомендуется уменьшить конфигурацию для экономии.',
        'severity': 'high', 'category': 'cost',
        'estimated_monthly_savings': 1800, 'confidence_score': 0.82,
        'metrics_snapshot': {'cpu_avg': 0.06, 'cpu_p95': 0.18},
    },
    {
        'source': 'seed_idle_vm',
        'recommendation_type': 'shutdown',
        'title': 'Остановить неиспользуемую VM (30 дней без нагрузки)',
        'description': 'Нет входящего трафика и загрузки CPU. Рекомендуется остановить ресурс.',
        'severity': 'critical', 'category': 'cost',
        'estimated_monthly_savings': 3200, 'confidence_score': 0.9,
        'metrics_snapshot': {'cpu_avg': 0.0, 'net_in': 0},
    },
    {
        'source': 'seed_unused_volume',
        'recommendation_type': 'cleanup',
        'title': 'Удалить неиспользуемый том 100 ГБ',
        'description': 'Том не подключён ни к одному инстансу более 45 дней.',
        'severity': 'medium', 'category': 'cost',
        'estimated_monthly_savings': 450, 'confidence_score': 0.78,
        'metrics_snapshot': {'attachments': 0, 'last_used_days': 45},
    },
    {
        'source': 'seed_cheaper_region',
        'recommendation_type': 'migrate',
        'title': 'Перенести в более дешёвый регион',
        'description': 'Стоимость в выбранном регионе на 25% ниже при сопоставимых параметрах.',
        'severity': 'low', 'category': 'cost',
        'estimated_monthly_savings': 700, 'confidence_score': 0.6,
        'metrics_snapshot': {'current_region': 'ru-msk', 'target_region': 'ru-spb'},
    },
    {
        'source': 'seed_rightsizing_ram',
        'recommendation_type': 'rightsizing',
        'title': 'Снизить RAM с 16 ГБ до 8 ГБ (низкое потребление)',
        'description': 'Пиковое использование памяти за 14 дней 38%.',
        'severity': 'medium', 'category': 'cost',
        'estimated_monthly_savings': 900, 'confidence_score': 0.75,
        'metrics_snapshot': {'mem_avg_gb': 3.1, 'mem_p95_gb': 6.2},
    },
    {
        'source': 'seed_storage_class',
        'recommendation_type': 'migrate',
        'title': 'Перевести бакет в класс хранения «инфреже»',
        'description': 'Низкая частота доступа (<1 раз/30 дней).',
        'severity': 'low', 'category': 'cost',
        'estimated_monthly_savings': 350, 'confidence_score': 0.65,
        'metrics_snapshot': {'access_per_30d': 0},
    },
    {
        'source': 'seed_delete_snapshots',
        'recommendation_type': 'cleanup',
        'title': 'Удалить устаревшие снапшоты (5 шт. > 60 дней)',
        'description': 'Снапшоты не привязаны к политикам бэкапа.',
        'severity': 'medium', 'category': 'cost',
        'estimated_monthly_savings': 520, 'confidence_score': 0.7,
        'metrics_snapshot': {'snapshots': 5, 'oldest_days': 120},
    },
    {
        'source': 'seed_resize_volume',
        'recommendation_type': 'rightsizing',
        'title': 'Уменьшить том с 200 ГБ до 120 ГБ',
        'description': 'Использование диска составляет 48% стабильно.',
        'severity': 'high', 'category': 'cost',
        'estimated_monthly_savings': 600, 'confidence_score': 0.72,
        'metrics_snapshot': {'disk_used_gb': 96, 'disk_size_gb': 200},
    },
    {
        'source': 'seed_commitment',
        'recommendation_type': 'commitment',
        'title': 'Перейти на помесячную подписку (скидка 15%)',
        'description': 'Стабильное использование за 90 дней, выгоден коммит.',
        'severity': 'info', 'category': 'cost',
        'estimated_monthly_savings': 800, 'confidence_score': 0.68,
        'metrics_snapshot': {'lookback_days': 90},
    },
    {
        'source': 'seed_cross_provider',
        'recommendation_type': 'migrate',
        'title': 'Мигрировать VM к провайдеру X (экономия 22%)',
        'description': 'Найдены эквивалентные характеристики у другого провайдера.',
        'severity': 'high', 'category': 'cost',
        'estimated_monthly_savings': 2100, 'confidence_score': 0.6,
        'metrics_snapshot': {'match_score': 0.86},
    },
]


def main():
    app = create_app()
    with app.app_context():
        # Pick any provider and resource if exist to link data; otherwise skip seeding gracefully
        provider = CloudProvider.query.first()
        resource = Resource.query.first()

        if not resource:
            print('⚠️  No resources found. Seed script skipped to avoid invalid foreign keys.')
            return

        # Idempotent cleanup: remove previous seeds by source prefix or known titles
        seed_sources = [s['source'] for s in SAMPLES] + [
            # old sources from the first version of the script
            'rightsizing_cpu', 'idle_vm', 'unused_volume', 'cheaper_region'
        ]
        OptimizationRecommendation.query.filter(
            OptimizationRecommendation.source.in_(seed_sources)
        ).delete(synchronize_session=False)
        db.session.commit()

        # Distribute seeds across first few resources if available
        resources = Resource.query.limit(5).all() or [resource]
        r_count = len(resources)

        for idx, sample in enumerate(SAMPLES):
            r = resources[idx % r_count]
            rec = OptimizationRecommendation(
                provider_id=r.provider_id,
                resource_id=r.id,
                resource_type=r.resource_type,
                resource_name=r.resource_name,
                title=sample['title'],
                description=sample['description'],
                recommendation_type=sample['recommendation_type'],
                severity=sample['severity'],
                category=sample['category'],
                estimated_monthly_savings=sample['estimated_monthly_savings'],
                confidence_score=sample['confidence_score'],
                source=sample['source'],
                metrics_snapshot=json.dumps(sample.get('metrics_snapshot', {})),
                insights=json.dumps({'explanation': 'Автоматически сгенерировано по метрикам'})
            )
            rec.first_seen_at = datetime.utcnow() - timedelta(days=1)
            db.session.add(rec)
        db.session.commit()
        print('✅ Seeded 10 sample recommendations')


if __name__ == '__main__':
    main()


