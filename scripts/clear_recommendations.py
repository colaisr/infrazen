import argparse
import os
import sys
from typing import List

from sqlalchemy import or_

# Ensure project root is on sys.path when running from scripts/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.core.database import db
from app.core.models.user import User
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource
from app.core.models.recommendations import OptimizationRecommendation
from app.core.models.pricing import PriceComparisonRecommendation


def clear_for_user(user: User) -> int:
    provider_ids: List[int] = [p.id for p in CloudProvider.query.filter_by(user_id=user.id).all()]
    resource_ids: List[int] = [r.id for r in Resource.query.filter(Resource.provider_id.in_(provider_ids)).all()]

    deleted_opt = OptimizationRecommendation.query.filter(
        or_(
            OptimizationRecommendation.provider_id.in_(provider_ids) if provider_ids else False,
            OptimizationRecommendation.resource_id.in_(resource_ids) if resource_ids else False,
        )
    ).delete(synchronize_session=False)

    deleted_price = PriceComparisonRecommendation.query.filter(
        or_(
            PriceComparisonRecommendation.user_id == user.id,
            PriceComparisonRecommendation.current_resource_id.in_(resource_ids) if resource_ids else False,
        )
    ).delete(synchronize_session=False)

    db.session.commit()
    return int(deleted_opt or 0) + int(deleted_price or 0)


def main():
    parser = argparse.ArgumentParser(description="Clear recommendations for a user")
    parser.add_argument("--user-email", dest="user_email", help="User email")
    parser.add_argument("--username", dest="username", help="Username")
    parser.add_argument("--user-id", dest="user_id", type=int, help="User ID")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        user = None
        if args.user_id:
            user = User.query.get(args.user_id)
        elif args.user_email:
            user = User.find_by_email(args.user_email)
        elif args.username:
            user = User.query.filter_by(username=args.username).first()
        if not user:
            raise SystemExit("User not found. Provide --user-id, --user-email, or --username")

        deleted = clear_for_user(user)
        print(f"Deleted {deleted} recommendations for user {user.id}")


if __name__ == "__main__":
    main()


