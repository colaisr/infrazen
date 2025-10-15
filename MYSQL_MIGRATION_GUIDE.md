# MySQL Migration Guide

This guide walks you through migrating InfraZen from SQLite to MySQL for both local development and production deployment on Beget.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local MySQL Setup](#local-mysql-setup)
3. [Data Migration](#data-migration)
4. [Demo User Setup](#demo-user-setup)
5. [Production Setup (Beget)](#production-setup-beget)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- Python 3.10+
- MySQL 8.0+ (local installation)
- Access to Beget control panel for production

### Install MySQL Python Driver

```bash
pip install pymysql cryptography
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

## Local MySQL Setup

### Step 1: Create MySQL Database

#### Option A: Using the Setup Script (Recommended)

```bash
chmod +x scripts/setup_local_mysql.sh
./scripts/setup_local_mysql.sh
```

The script will create:
- Database: `infrazen_dev`
- User: `infrazen_user`
- Password: `infrazen_password`

#### Option B: Manual Setup

```sql
-- Connect to MySQL as root
mysql -u root -p

-- Create database
CREATE DATABASE infrazen_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'infrazen_user'@'localhost' IDENTIFIED BY 'infrazen_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON infrazen_dev.* TO 'infrazen_user'@'localhost';

-- Flush privileges
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES LIKE 'infrazen_dev';
```

### Step 2: Update Configuration

Update your `config.env` file:

```bash
# MySQL Local Development
DATABASE_URL=mysql+pymysql://infrazen_user:infrazen_password@localhost:3306/infrazen_dev?charset=utf8mb4
```

Or use the provided `config.env.dev` file:

```bash
cp config.env.dev config.env
# Edit config.env with your actual credentials
```

### Step 3: Initialize MySQL Schema

```bash
python init_database.py
```

This will:
- Create all database tables
- Create super admin user (admin@infrazen.com / kok5489103)
- Seed demo user with mock data

## Data Migration

### Step 1: Export Existing SQLite Data

Before switching to MySQL, export your existing SQLite data:

```bash
python scripts/export_sqlite_data.py
```

This creates `sqlite_export.json` with all your current data.

### Step 2: Import Data to MySQL

After initializing the MySQL schema, import your data:

```bash
python scripts/import_data_to_mysql.py
```

The script will:
- Read the JSON export
- Import all data preserving IDs and relationships
- Validate data integrity
- Show import statistics

### Step 3: Verify Migration

Check that all data was migrated correctly:

```bash
python -c "
from app import create_app
from app.core.database import db
from app.core.models.user import User
from app.core.models.provider import CloudProvider
from app.core.models.resource import Resource

app = create_app()
with app.app_context():
    print(f'Users: {User.query.count()}')
    print(f'Providers: {CloudProvider.query.count()}')
    print(f'Resources: {Resource.query.count()}')
"
```

## Demo User Setup

### What is the Demo User?

The demo user (`demo@infrazen.com`) is a special account with mock data used for:
- Platform demonstrations
- Testing new features
- Onboarding new users

### Demo User Features

- **Email**: demo@infrazen.com
- **Password**: demo
- **Providers**: 2 (Beget VPS + Selectel Cloud)
- **Resources**: 7 mock resources
- **Recommendations**: 3 cost optimization suggestions
- **Protected**: Cannot be deleted (protection coming in future phase)

### Reseed Demo User

Admin users can reset the demo user data at any time:

1. Login as admin (admin@infrazen.com / kok5489103)
2. Go to Admin Dashboard
3. Click "Reseed Demo User" button

Or via command line:

```bash
python scripts/seed_demo_user.py
```

## Production Setup (Beget)

### Step 1: Provision MySQL on Beget

1. Login to [Beget Control Panel](https://cp.beget.com/)
2. Navigate to **MySQL** section
3. Create new database:
   - Database name: `infrazen_prod`
   - Charset: `utf8mb4`
   - Note the credentials provided

### Step 2: Configure Remote Access (if needed)

If deploying from external server:
1. In Beget control panel, go to MySQL settings
2. Add your server IP to allowed hosts
3. Enable remote connections

### Step 3: Create Production Environment File

On your Beget VPS, create `config.env.prod`:

```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=YOUR_SECURE_RANDOM_KEY_HERE

# Database Configuration - Beget MySQL
DATABASE_URL=mysql+pymysql://YOUR_BEGET_USER:YOUR_BEGET_PASS@mysql.beget.com:3306/infrazen_prod?charset=utf8mb4

# Google OAuth (Production)
GOOGLE_CLIENT_ID=your-production-google-client-id.apps.googleusercontent.com

# Logging
LOG_LEVEL=INFO
```

**Important**: Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 4: Deploy Application

On your Beget VPS:

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_database.py

# Optional: Import data from backup
python scripts/import_data_to_mysql.py sqlite_export.json

# Start application with Gunicorn
gunicorn -k uvicorn.workers.UvicornWorker app.web.main:app \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --access-logfile - \
  --error-logfile -
```

### Step 5: Configure Systemd Service (Optional)

Create `/etc/systemd/system/infrazen.service`:

```ini
[Unit]
Description=InfraZen FinOps Platform
After=network.target mysql.service

[Service]
Type=notify
User=your_user
WorkingDirectory=/path/to/InfraZen
Environment="PATH=/path/to/venv/bin"
EnvironmentFile=/path/to/InfraZen/config.env.prod
ExecStart=/path/to/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker app.web.main:app --bind 0.0.0.0:8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable infrazen
sudo systemctl start infrazen
sudo systemctl status infrazen
```

## Troubleshooting

### Connection Errors

**Error**: `Can't connect to MySQL server`

**Solution**:
```bash
# Check MySQL is running
sudo systemctl status mysql

# Test connection
mysql -u infrazen_user -p infrazen_dev
```

### Character Set Issues

**Error**: `Incorrect string value`

**Solution**: Ensure database uses utf8mb4:

```sql
ALTER DATABASE infrazen_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Import Failures

**Error**: Foreign key constraint fails

**Solution**: Import tables in correct order (handled automatically by import script)

### Migration Rollback

If you need to rollback to SQLite:

```bash
# Update config.env
DATABASE_URL=sqlite:///instance/dev.db

# Restart application
python run.py
```

Your SQLite database is preserved in `instance/dev.db` and the backup JSON file.

### Performance Issues

**Symptom**: Slow queries

**Solutions**:

1. Check connection pool settings in `app/config.py`:
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
```

2. Enable query logging to identify slow queries:
```python
SQLALCHEMY_ECHO = True
```

3. Add indexes for frequently queried columns

### Demo User Issues

**Problem**: Demo user missing or has no data

**Solution**:
```bash
python scripts/seed_demo_user.py
```

**Problem**: Can't delete demo user providers

**Note**: Demo user protection will be implemented in a future phase. For now, admins can reseed the demo user to reset its data.

## Database Backups

### Backup MySQL Database

```bash
mysqldump -u infrazen_user -p infrazen_dev > infrazen_backup_$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
mysql -u infrazen_user -p infrazen_dev < infrazen_backup_20250101.sql
```

### Automated Backups (Cron)

Add to crontab:

```bash
0 2 * * * mysqldump -u infrazen_user -p'infrazen_password' infrazen_dev > /backups/infrazen_$(date +\%Y\%m\%d).sql
```

## Next Steps

After successful migration:

1. ✅ Test all application features
2. ✅ Verify provider syncs work correctly
3. ✅ Test authentication (Google OAuth + password)
4. ✅ Test admin functions
5. ✅ Set up automated backups
6. ✅ Configure monitoring and logging
7. ✅ Update documentation

## Support

For issues or questions:
- Check the troubleshooting section above
- Review application logs: `tail -f server.log`
- Check MySQL error log: `tail -f /var/log/mysql/error.log`

