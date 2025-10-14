"""
Migration: Extend optimization_recommendations with additional fields
This migration is SQLite-friendly and uses conditional ALTER TABLE ADD COLUMN
statements to avoid failures when columns already exist.
"""
from app.core.database import db


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    try:
        result = connection.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
        return any(row[1] == column_name for row in result)
    except Exception:
        return False


def _add_column_if_missing(connection, table: str, column: str, ddl: str):
    if not _column_exists(connection, table, column):
        connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def upgrade():
    table = 'optimization_recommendations'
    with db.engine.begin() as connection:
        # Relations and cached fields
        _add_column_if_missing(connection, table, 'provider_id', 'INTEGER')
        _add_column_if_missing(connection, table, 'category', "VARCHAR(20) DEFAULT 'cost'")
        _add_column_if_missing(connection, table, 'severity', "VARCHAR(10) DEFAULT 'medium'")
        _add_column_if_missing(connection, table, 'source', 'VARCHAR(50)')
        _add_column_if_missing(connection, table, 'resource_type', 'VARCHAR(50)')
        _add_column_if_missing(connection, table, 'resource_name', 'VARCHAR(200)')

        # Savings
        _add_column_if_missing(connection, table, 'estimated_monthly_savings', 'FLOAT DEFAULT 0.0')
        _add_column_if_missing(connection, table, 'estimated_one_time_savings', 'FLOAT DEFAULT 0.0')

        # JSON payloads stored as TEXT
        _add_column_if_missing(connection, table, 'metrics_snapshot', 'TEXT')
        _add_column_if_missing(connection, table, 'insights', 'TEXT')

        # Lifecycle
        _add_column_if_missing(connection, table, 'first_seen_at', 'DATETIME')
        _add_column_if_missing(connection, table, 'seen_at', 'DATETIME')
        _add_column_if_missing(connection, table, 'snoozed_until', 'DATETIME')
        _add_column_if_missing(connection, table, 'dismissed_at', 'DATETIME')
        _add_column_if_missing(connection, table, 'dismissed_reason', 'TEXT')

        # Backfill first_seen_at from created_at where NULL
        try:
            connection.exec_driver_sql(
                "UPDATE optimization_recommendations SET first_seen_at = created_at WHERE first_seen_at IS NULL"
            )
        except Exception:
            pass


def downgrade():
    # No-op for safety on SQLite
    print('⚠️  Downgrade not implemented for this migration')


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        upgrade()


