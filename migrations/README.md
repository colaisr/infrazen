# Database Migrations with Alembic

This directory contains Alembic database migrations for the InfraZen application.

## Current Status

- **Baseline Migration**: `1d8b3833a084_initial_baseline_migration.py` - Represents the current database state
- **Status**: Applied to both local dev and production databases

## Creating New Migrations

### Local Development

1. Make changes to your models in `app/core/models/`
2. Create a new migration:
   ```bash
   python scripts/create_migration.py "Description of changes"
   ```
3. Review the generated migration file in `migrations/versions/`
4. Test the migration locally:
   ```bash
   DATABASE_URL=mysql+pymysql://infrazen_user:infrazen_password@localhost:3306/infrazen_dev?charset=utf8mb4 python3 -m alembic upgrade head
   ```

### Production Deployment

The deploy script automatically runs migrations:
```bash
./deploy
```

## Migration Commands

- **Check current status**: `python3 -m alembic current`
- **Show migration history**: `python3 -m alembic history`
- **Upgrade to latest**: `python3 -m alembic upgrade head`
- **Downgrade one step**: `python3 -m alembic downgrade -1`

## Important Notes

- Always test migrations locally before deploying
- Review auto-generated migrations before committing
- The deploy script uses `alembic upgrade head` to apply all pending migrations
- Migrations are applied automatically during deployment
