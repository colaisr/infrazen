# Next Steps: MySQL Migration

## 🎯 Current Status

✅ **Implementation Complete**

All code, scripts, and documentation have been created and are ready for testing.

## 📝 What You Need To Do Now

### Step 1: Install MySQL Driver (1 minute)

```bash
cd /Users/colakamornik/Desktop/InfraZen
pip install pymysql cryptography
```

### Step 2: Setup Local MySQL Database (2 minutes)

You mentioned you have a local MySQL instance running. Let's use it:

```bash
# Run the setup script
./scripts/setup_local_mysql.sh
```

This will prompt for your MySQL root password and create:
- Database: `infrazen_dev`
- User: `infrazen_user`
- Password: `infrazen_password`

**Alternative**: If you prefer different credentials, manually create the database:

```sql
mysql -u root -p

CREATE DATABASE infrazen_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'infrazen_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON infrazen_dev.* TO 'infrazen_user'@'localhost';
FLUSH PRIVILEGES;
```

### Step 3: Update Configuration (1 minute)

Edit `config.env`:

```bash
DATABASE_URL=mysql+pymysql://infrazen_user:infrazen_password@localhost:3306/infrazen_dev?charset=utf8mb4
```

Or copy the dev template:

```bash
cp config.env.dev config.env
# Then edit config.env with your actual credentials
```

### Step 4: Backup Current SQLite Data (1 minute)

```bash
python scripts/export_sqlite_data.py
```

This creates `sqlite_export.json` with all your current data.

### Step 5: Initialize MySQL Database (1 minute)

```bash
python init_database.py
```

This will:
- Create all tables
- Create super admin: `admin@infrazen.com` / `kok5489103`
- Create demo user: `demo@infrazen.com` / `demo` with mock data

### Step 6: Import Your Existing Data (2 minutes)

```bash
python scripts/import_data_to_mysql.py
```

This imports your existing users, providers, resources, etc. from the SQLite backup.

### Step 7: Validate Setup (1 minute)

```bash
python scripts/validate_mysql_setup.py
```

This checks:
- Database connection
- All tables created
- Data imported correctly
- Demo user has data
- Query performance

### Step 8: Test the Application (5 minutes)

```bash
python run.py
```

Visit http://localhost:5000

**Test these features:**
- [ ] Login as super admin (admin@infrazen.com / kok5489103)
- [ ] Check users in admin panel
- [ ] Login as demo user (demo@infrazen.com / demo)
- [ ] View demo user's providers and resources
- [ ] Test admin reseed button (Admin Dashboard → Reseed Demo User)
- [ ] Add a new cloud provider
- [ ] Run a sync operation

## 🔍 Verification Checklist

After completing the steps above, verify:

### Database
- [ ] MySQL database `infrazen_dev` exists
- [ ] Can connect to database
- [ ] All tables created successfully
- [ ] Super admin user exists
- [ ] Demo user exists with data

### Application
- [ ] Application starts without errors
- [ ] Dashboard loads correctly
- [ ] Authentication works (both Google OAuth and password)
- [ ] Admin panel accessible
- [ ] Demo user has visible resources
- [ ] Provider connections page works
- [ ] Resources page displays data

### Migration
- [ ] Existing users migrated
- [ ] Existing providers migrated
- [ ] Existing resources migrated
- [ ] Sync history preserved
- [ ] Recommendations migrated

## 🚀 Production Deployment (When Ready)

### Beget MySQL Setup

1. **Provision MySQL on Beget**
   - Go to https://cp.beget.com/
   - Navigate to MySQL section
   - Create new database: `infrazen_prod`
   - Note the credentials provided

2. **Configure Production Environment**
   
   On your Beget VPS, create `config.env`:
   
   ```bash
   FLASK_ENV=production
   SECRET_KEY=<generate_secure_key>
   DATABASE_URL=mysql+pymysql://beget_user:beget_pass@mysql.beget.com:3306/infrazen_prod?charset=utf8mb4
   GOOGLE_CLIENT_ID=<your_production_client_id>
   ```

3. **Initialize Production Database**
   
   ```bash
   python init_database.py
   ```

4. **Deploy Application**
   
   ```bash
   gunicorn -k uvicorn.workers.UvicornWorker app.web.main:app \
     --bind 0.0.0.0:8000 \
     --workers 2
   ```

## 📚 Documentation

- **Quick Start**: [QUICK_START_MYSQL.md](./QUICK_START_MYSQL.md)
- **Full Guide**: [MYSQL_MIGRATION_GUIDE.md](./MYSQL_MIGRATION_GUIDE.md)
- **Implementation Details**: [MYSQL_IMPLEMENTATION_SUMMARY.md](./MYSQL_IMPLEMENTATION_SUMMARY.md)

## 🆘 If Something Goes Wrong

### Can't connect to MySQL?

```bash
# Check MySQL is running
sudo systemctl status mysql

# Check credentials
mysql -u infrazen_user -p infrazen_dev
```

### Import fails?

```bash
# Re-initialize database
python init_database.py

# Try import again
python scripts/import_data_to_mysql.py
```

### Demo user has no data?

```bash
# Reseed demo user
python scripts/seed_demo_user.py
```

### Want to rollback to SQLite?

```bash
# Edit config.env
DATABASE_URL=sqlite:///instance/dev.db

# Restart application
python run.py
```

Your SQLite database is still at `instance/dev.db` and remains unchanged.

## 🎉 Success Criteria

You'll know everything is working when:

1. ✅ Application starts without errors
2. ✅ Can login as admin and demo user
3. ✅ Demo user shows 2 providers and 7 resources
4. ✅ Admin reseed button works
5. ✅ Can add new providers
6. ✅ Sync operations complete successfully
7. ✅ All existing data is accessible

## 📞 Questions?

If you encounter any issues:

1. Check the validation script output:
   ```bash
   python scripts/validate_mysql_setup.py
   ```

2. Check application logs:
   ```bash
   tail -f server.log
   ```

3. Check MySQL logs:
   ```bash
   tail -f /var/log/mysql/error.log
   ```

4. Review the troubleshooting section in [MYSQL_MIGRATION_GUIDE.md](./MYSQL_MIGRATION_GUIDE.md)

---

**Ready to start?** Run Step 1 above! 🚀

