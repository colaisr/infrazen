import os
import sys
import re
from typing import Optional
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.core.database import db
from app.core.models.user import User
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.pricing import ProviderPrice


def parse_vcpu(cfg) -> Optional[int]:
    if not isinstance(cfg, dict):
        return None
    cpu_field = cfg.get('cpu') or cfg.get('vcpu') or cfg.get('cores')
    if not cpu_field:
        return None
    m = re.search(r"(\d+)", str(cpu_field))
    return int(m.group(1)) if m else None


def parse_ram_gb(cfg) -> Optional[int]:
    if not isinstance(cfg, dict):
        return None
    mem = cfg.get('memory') or cfg.get('ram_gb')
    if not mem:
        return None
    m = re.search(r"(\d+)", str(mem))
    return int(m.group(1)) if m else None


def main(username_or_email: Optional[str] = None, user_id: Optional[int] = None):
    app = create_app()
    with app.app_context():
        # Resolve user
        user = None
        if user_id:
            user = User.query.get(user_id)
        elif username_or_email:
            user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        if not user:
            print(f"User not found")
            return 1

        # Beget providers for user
        beget_providers = CloudProvider.query.filter_by(user_id=user.id, provider_type='beget').all()
        beget_ids = [p.id for p in beget_providers]
        print(f"User {user.id}: {len(beget_ids)} Beget providers -> {beget_ids}")

        # Resources (servers)
        servers = Resource.query.filter(
            Resource.provider_id.in_(beget_ids),
            Resource.resource_type.in_(['server', 'vm'])
        ).all()
        print(f"Found {len(servers)} Beget servers")

        # For each server, compare with Selectel prices
        for r in servers:
            cfg = r.get_provider_config() if hasattr(r, 'get_provider_config') else {}
            vcpu = parse_vcpu(cfg) or 0
            ram = parse_ram_gb(cfg) or 0
            region = (r.region or '')
            prefix = region[:2] if region else ''
            # Current monthly cost baseline
            if r.billing_period == 'monthly' and r.effective_cost:
                current_monthly = float(r.effective_cost)
            elif r.daily_cost:
                current_monthly = float(r.daily_cost) * 30.0
            else:
                current_monthly = 0.0

            print(f"\nResource {r.resource_name} (vcpu={vcpu}, ram={ram}GB, region={region}) current≈{int(current_monthly)} {r.currency or 'RUB'}/mo")

            q = ProviderPrice.query.filter(
                ProviderPrice.provider == 'selectel',
                ProviderPrice.cpu_cores.isnot(None),
                ProviderPrice.ram_gb.isnot(None)
            )
            if prefix:
                q = q.filter(ProviderPrice.region.startswith(prefix))

            # Simple equivalence: exact vcpu and RAM within ±20%
            candidates = []
            for p in q.limit(1000).all():
                if p.cpu_cores != vcpu:
                    continue
                if not p.ram_gb:
                    continue
                low = int(0.8 * ram) if ram else 0
                high = int(1.2 * ram) if ram else 0
                if ram and not (low <= int(p.ram_gb) <= high):
                    continue
                if not p.monthly_cost:
                    continue
                candidates.append(p)

            if not candidates:
                print("  No Selectel candidates matching CPU/RAM/region prefix")
                continue

            best = min(candidates, key=lambda x: float(x.monthly_cost or 1e12))
            best_cost = float(best.monthly_cost)
            savings = current_monthly - best_cost
            print(f"  Best Selectel: {best.provider_sku} {best.region} ≈{int(best_cost)} {best.currency or 'RUB'}/mo | savings≈{int(savings)}")

    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', type=str)
    parser.add_argument('--email', type=str)
    parser.add_argument('--user-id', type=int)
    args = parser.parse_args()
    username_or_email = args.username or args.email
    sys.exit(main(username_or_email=username_or_email, user_id=args.user_id))


