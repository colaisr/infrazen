from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Any


def _rub(value: float) -> int:
    """Return rounded ruble value as int for clean UI numbers."""
    return int(round(value))


def generate_expense_trend(days: int = 30) -> List[Dict[str, Any]]:
    today = date.today()
    base = 185000.0  # ₽ monthly-ish baseline across both clouds
    # Create a slight downward trend to reflect optimizations
    trend: List[Dict[str, Any]] = []
    for i in range(days):
        d = today - timedelta(days=(days - i - 1))
        # oscillate +/-5% with an overall -12.5% slope
        factor = 1.0 - 0.125 * (i / max(days - 1, 1))
        oscillation = (0.05 * ((i % 7) - 3) / 3.0)
        value = base * factor * (1.0 + oscillation)
        trend.append({
            'date': d.isoformat(),
            'amount_rub': _rub(value)
        })
    return trend


def get_connected_providers() -> List[Dict[str, Any]]:
    return [
        {
            'id': 'yandex-cloud',
            'code': 'yc',
            'name': 'Yandex Cloud',
            'connection_name': 'Основной аккаунт YC',
            'status': 'connected',
            'added_at': (date.today() - timedelta(days=14)).isoformat(),
            'details': {
                'organization_id': 'org-ydx-demo',
                'cloud_id': 'b1g-demo-cloud',
                'folder_id': 'b1g-demo-folder',
                'regions': ['ru-central1-a', 'ru-central1-b'],
            }
        },
        {
            'id': 'selectel',
            'code': 'sel',
            'name': 'Selectel',
            'connection_name': 'Продакшн Selectel',
            'status': 'connected',
            'added_at': (date.today() - timedelta(days=10)).isoformat(),
            'details': {
                'project_id': 'prj-sel-demo',
                'regions': ['msk-a', 'spb-a'],
            }
        }
    ]


def get_resources() -> List[Dict[str, Any]]:
    # Minimal but realistic mix of resources across two providers
    return [
        # Yandex Cloud compute instances
        {
            'id': 'yc-vm-001', 'provider': 'Yandex Cloud', 'type': 'vm', 'name': 'prod-api-ru-a',
            'region': 'ru-central1-a', 'status': 'RUNNING', 'vcpu': 8, 'memory_gb': 32,
            'disks_gb': 200, 'platform': 'Intel Ice Lake', 'tags': ['env:prod', 'team:core'],
            'monthly_cost_rub': _rub(34500)
        },
        {
            'id': 'yc-vm-002', 'provider': 'Yandex Cloud', 'type': 'vm', 'name': 'batch-jobs-ru-b',
            'region': 'ru-central1-b', 'status': 'STOPPED', 'vcpu': 4, 'memory_gb': 16,
            'disks_gb': 100, 'platform': 'Intel Cascade Lake', 'tags': ['env:dev', 'team:data'],
            'monthly_cost_rub': _rub(11800)
        },
        {
            'id': 'yc-disk-001', 'provider': 'Yandex Cloud', 'type': 'disk', 'name': 'prod-api-boot',
            'region': 'ru-central1-a', 'status': 'IN_USE', 'size_gb': 50, 'disk_type': 'network-ssd',
            'attached_to': 'yc-vm-001', 'monthly_cost_rub': _rub(900)
        },
        {
            'id': 'yc-bucket-001', 'provider': 'Yandex Cloud', 'type': 'bucket', 'name': 'logs-prod-archive',
            'region': 'ru-central1', 'status': 'ACTIVE', 'storage_gb': 2800, 'class': 'cold',
            'monthly_cost_rub': _rub(12500)
        },

        # Selectel compute instances
        {
            'id': 'sel-vm-101', 'provider': 'Selectel', 'type': 'vm', 'name': 'web-frontend-msk',
            'region': 'msk-a', 'status': 'RUNNING', 'vcpu': 4, 'memory_gb': 8,
            'disks_gb': 80, 'flavor': 'standard-4-8', 'tags': ['env:prod', 'app:web'],
            'monthly_cost_rub': _rub(9800)
        },
        {
            'id': 'sel-vm-102', 'provider': 'Selectel', 'type': 'vm', 'name': 'db-postgres-spb',
            'region': 'spb-a', 'status': 'RUNNING', 'vcpu': 8, 'memory_gb': 32,
            'disks_gb': 500, 'flavor': 'memory-8-32', 'tags': ['env:prod', 'tier:db'],
            'monthly_cost_rub': _rub(40250)
        },
        {
            'id': 'sel-volume-201', 'provider': 'Selectel', 'type': 'volume', 'name': 'pg-data-01',
            'region': 'spb-a', 'status': 'IN_USE', 'size_gb': 500, 'volume_type': 'ssd',
            'attached_to': 'sel-vm-102', 'monthly_cost_rub': _rub(3200)
        },
        {
            'id': 'sel-bucket-301', 'provider': 'Selectel', 'type': 'bucket', 'name': 'static-assets',
            'region': 'msk', 'status': 'ACTIVE', 'storage_gb': 750, 'class': 'standard',
            'monthly_cost_rub': _rub(4200)
        }
    ]


def get_usage_summary() -> Dict[str, Any]:
    # Aggregate plausible usage across resources
    return {
        'cpu': {'used_vcpu': 236, 'available_vcpu': 350, 'percent': 67},
        'ram': {'used_gb': 1229, 'available_gb': 1515, 'percent': 81},
        'storage': {'used_tb': 8.6, 'available_tb': 20.0, 'percent': 43},
        'network': {'used_tb': 2.9, 'limit_tb': 10.0, 'percent': 29}
    }


def get_recommendations() -> List[Dict[str, Any]]:
    return [
        {
            'id': 'rec-001',
            'provider': 'Yandex Cloud',
            'category': 'rightsize',
            'resource_id': 'yc-vm-001',
            'title': 'Понизить vCPU с 8 до 6 для prod-api-ru-a',
            'estimated_savings_rub': _rub(6200),
            'confidence': 0.82
        },
        {
            'id': 'rec-002',
            'provider': 'Selectel',
            'category': 'cleanup',
            'resource_id': 'sel-volume-201',
            'title': 'Удалить неиспользуемые снепшоты на pg-data-01',
            'estimated_savings_rub': _rub(1800),
            'confidence': 0.9
        },
        {
            'id': 'rec-003',
            'provider': 'Yandex Cloud',
            'category': 'storage-policy',
            'resource_id': 'yc-bucket-001',
            'title': 'Включить lifecycle policy для архивных логов',
            'estimated_savings_rub': _rub(2400),
            'confidence': 0.76
        }
    ]


def get_overview() -> Dict[str, Any]:
    resources = get_resources()
    providers = get_connected_providers()
    total_expenses = sum(r.get('monthly_cost_rub', 0) for r in resources)
    potential_savings = sum(r['estimated_savings_rub'] for r in get_recommendations())
    return {
        'kpis': {
            'total_expenses_rub': _rub(total_expenses),
            'potential_savings_rub': _rub(potential_savings),
            'active_resources': len(resources),
            'connected_providers': len(providers)
        },
        'trend': generate_expense_trend(),
        'usage': get_usage_summary(),
        'providers': providers,
        'resources': resources,
        'recommendations': get_recommendations()
    }

def get_beget_mock_resources() -> Dict[str, Any]:
    """Get mock Beget hosting resources"""
    return {
        'account_info': {
            'account_id': 'beget_demo_123',
            'username': 'demo_user',
            'status': 'active',
            'plan': 'Standard',
            'balance': 1500.0,
            'currency': 'RUB',
            'created_date': '2020-01-15',
            'domains_count': 2,
            'databases_count': 2,
            'ftp_accounts_count': 2
        },
        'domains': [
            {
                'id': 'domain_1',
                'name': 'example.ru',
                'status': 'active',
                'registrar': 'Beget',
                'registration_date': '2020-01-15',
                'expiration_date': '2025-01-15',
                'nameservers': ['ns1.beget.com', 'ns2.beget.com'],
                'hosting_plan': 'Standard',
                'monthly_cost': 150.0
            },
            {
                'id': 'domain_2',
                'name': 'mysite.com',
                'status': 'active',
                'registrar': 'Beget',
                'registration_date': '2021-03-20',
                'expiration_date': '2026-03-20',
                'nameservers': ['ns1.beget.com', 'ns2.beget.com'],
                'hosting_plan': 'Premium',
                'monthly_cost': 300.0
            }
        ],
        'databases': [
            {
                'id': 'db_1',
                'name': 'myapp_db',
                'type': 'mysql',
                'size_mb': 250,
                'username': 'myapp_user',
                'host': 'mysql.beget.com',
                'port': 3306,
                'monthly_cost': 50.0
            },
            {
                'id': 'db_2',
                'name': 'blog_db',
                'type': 'mysql',
                'size_mb': 120,
                'username': 'blog_user',
                'host': 'mysql.beget.com',
                'port': 3306,
                'monthly_cost': 30.0
            }
        ],
        'ftp_accounts': [
            {
                'id': 'ftp_1',
                'username': 'main_ftp',
                'home_directory': '/public_html',
                'disk_quota_mb': 1024,
                'disk_used_mb': 450,
                'server_host': 'ftp.beget.com',
                'port': 21,
                'is_active': True,
                'monthly_cost': 25.0
            },
            {
                'id': 'ftp_2',
                'username': 'backup_ftp',
                'home_directory': '/backups',
                'disk_quota_mb': 512,
                'disk_used_mb': 200,
                'server_host': 'ftp.beget.com',
                'port': 21,
                'is_active': True,
                'monthly_cost': 15.0
            }
        ],
        'billing_info': {
            'current_balance': 1500.0,
            'currency': 'RUB',
            'last_payment': '2024-01-15',
            'next_payment': '2024-02-15',
            'monthly_cost': 555.0,
            'payment_method': 'Credit Card',
            'auto_renewal': True
        },
        'usage_stats': {
            'disk_usage_mb': 670,
            'disk_limit_mb': 2048,
            'bandwidth_usage_gb': 45,
            'bandwidth_limit_gb': 100,
            'email_accounts_used': 5,
            'email_accounts_limit': 10,
            'databases_used': 2,
            'databases_limit': 5
        }
    }


