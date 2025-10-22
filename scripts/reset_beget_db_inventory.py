"""
Reset Beget inventory for testing the promote flow:
 - Remove ProviderResourceType entries for Beget with unified_type in ['DB','database']
 - Delete all UnrecognizedResource rows for Beget providers

Usage:
  "./venv 2/bin/python" scripts/reset_beget_db_inventory.py
"""
from __future__ import annotations

import sys
from typing import List


def main() -> int:
    import os
    import sys as _sys
    _root = os.path.dirname(os.path.dirname(__file__))
    if _root not in _sys.path:
        _sys.path.insert(0, _root)

    from app import create_app
    from app.core.models import db
    from app.core.models.provider import CloudProvider
    from app.core.models.provider_resource_type import ProviderResourceType
    from app.core.models.unrecognized_resource import UnrecognizedResource

    app = create_app()
    with app.app_context():
        removed_prt = 0
        removed_unrec = 0

        # Remove known type entries (both uppercase and lowercase variants)
        targets: List[str] = ["DB", "database"]
        rows = (
            ProviderResourceType.query
            .filter(ProviderResourceType.provider_type == 'beget')
            .filter(ProviderResourceType.unified_type.in_(targets))
            .all()
        )
        for r in rows:
            db.session.delete(r)
            removed_prt += 1

        # Find Beget provider IDs
        provider_ids = [p.id for p in CloudProvider.query.filter_by(provider_type='beget').all()]

        if provider_ids:
            # Delete unrecognized resources for those providers
            q = UnrecognizedResource.query.filter(UnrecognizedResource.provider_id.in_(provider_ids))
            removed_unrec = q.count()
            for item in q.all():
                db.session.delete(item)

        db.session.commit()

        print(f"Removed ProviderResourceType rows (beget: DB/database): {removed_prt}")
        print(f"Deleted UnrecognizedResource rows for beget: {removed_unrec}")

    return 0


if __name__ == "__main__":
    sys.exit(main())


