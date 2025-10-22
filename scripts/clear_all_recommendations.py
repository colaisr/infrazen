import os
import sys

# Ensure project root is on sys.path when running from scripts/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.core.database import db
from app.core.models.recommendations import OptimizationRecommendation
from app.core.models.pricing import PriceComparisonRecommendation


def main():
    app = create_app()
    with app.app_context():
        deleted_opt = db.session.query(OptimizationRecommendation).delete(synchronize_session=False)
        deleted_price = db.session.query(PriceComparisonRecommendation).delete(synchronize_session=False)
        db.session.commit()
        print(f"Deleted {int(deleted_opt or 0)} OptimizationRecommendation and {int(deleted_price or 0)} PriceComparisonRecommendation records")


if __name__ == "__main__":
    main()







