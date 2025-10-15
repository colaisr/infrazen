# Quick Start: MySQL Migration

This is a streamlined guide to get InfraZen running on MySQL quickly.

## 🚀 Quick Setup (5 minutes)

### 1. Install MySQL Driver

```bash
pip install pymysql cryptography
```

### 2. Setup Local MySQL Database

```bash
./scripts/setup_local_mysql.sh
```

This creates:
- Database: `infrazen_dev`
- User: `infrazen_user`  
- Password: `infrazen_password`

### 3. Update Configuration

```bash
# Edit config.env and add:
DATABASE_URL=mysql+pymysql://infrazen_user:infrazen_password@localhost:3306/infrazen_dev?charset=utf8mb4
```

### 4. Initialize Database

```bash
python init_database.py
```

This will:
- ✅ Create all tables
- ✅ Create super admin (admin@infrazen.com / kok5489103)
- ✅ Create demo user with mock data

### 5. (Optional) Migrate Existing Data

```bash
# Export SQLite data
python scripts/export_sqlite_data.py

# Import to MySQL
python scripts/import_data_to_mysql.py
```

### 6. Validate Setup

```bash
python scripts/validate_mysql_setup.py
```

### 7. Start Application

```bash
python run.py
```

Visit: http://localhost:5000

## 📝 Quick Reference

### Default Users

| Email | Password | Role |
|-------|----------|------|
| admin@infrazen.com | kok5489103 | Super Admin |
| demo@infrazen.com | demo | Demo User |

### Database Credentials

| Setting | Value |
|---------|-------|
| Host | localhost |
| Port | 3306 |
| Database | infrazen_dev |
| User | infrazen_user |
| Password | infrazen_password |

### Useful Commands

```bash
# Check MySQL is running
sudo systemctl status mysql

# Connect to database
mysql -u infrazen_user -p infrazen_dev

# Reseed demo user
python scripts/seed_demo_user.py

# Validate setup
python scripts/validate_mysql_setup.py

# Export data backup
python scripts/export_sqlite_data.py

# Import data from backup
python scripts/import_data_to_mysql.py
```

### Admin Features

1. **Reseed Demo User**
   - Login as admin
   - Go to Admin Dashboard
   - Click "Reseed Demo User"

2. **View All Users**
   - Admin Panel → Users

3. **Manage Providers**
   - Admin Panel → Providers

## 🔧 Troubleshooting

### Can't connect to MySQL?

```bash
# Check MySQL is running
sudo systemctl status mysql

# Restart MySQL
sudo systemctl restart mysql
```

### Database not found?

```bash
# Run setup script again
./scripts/setup_local_mysql.sh
```

### Missing tables?

```bash
# Initialize database
python init_database.py
```

### Demo user has no data?

```bash
# Reseed demo user
python scripts/seed_demo_user.py
```

## 📚 Full Documentation

See [MYSQL_MIGRATION_GUIDE.md](./MYSQL_MIGRATION_GUIDE.md) for complete documentation.

## 🎯 Next Steps

1. ✅ Test authentication (Google OAuth + password)
2. ✅ Add cloud provider connections
3. ✅ Run sync to fetch resources
4. ✅ View cost analytics
5. ✅ Check recommendations

## 🐛 Need Help?

- Check logs: `tail -f server.log`
- Validate setup: `python scripts/validate_mysql_setup.py`
- Review: [MYSQL_MIGRATION_GUIDE.md](./MYSQL_MIGRATION_GUIDE.md)

