# MySQL Migration Checklist

Track your progress through the MySQL migration process.

## 📋 Pre-Migration Checklist

- [ ] MySQL 8.0+ installed and running locally
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Current SQLite database backed up
- [ ] Google OAuth credentials ready (if using)
- [ ] Beget account created (for production)

## 🔧 Local Development Setup

### Phase 1: Database Setup
- [ ] Run `./scripts/setup_local_mysql.sh`
- [ ] MySQL database `infrazen_dev` created
- [ ] MySQL user `infrazen_user` created with privileges
- [ ] Updated `config.env` with MySQL DATABASE_URL

### Phase 2: Schema Initialization
- [ ] Run `python init_database.py`
- [ ] All database tables created
- [ ] Super admin user created (admin@infrazen.com)
- [ ] Demo user created with mock data

### Phase 3: Data Migration
- [ ] Run `python scripts/export_sqlite_data.py`
- [ ] SQLite export completed (`sqlite_export.json` created)
- [ ] Run `python scripts/import_data_to_mysql.py`
- [ ] All data imported successfully
- [ ] Data integrity verified

### Phase 4: Validation
- [ ] Run `python scripts/validate_mysql_setup.py`
- [ ] Database connection successful
- [ ] All required tables present
- [ ] Data counts correct
- [ ] Query performance acceptable

## 🧪 Testing

### Application Testing
- [ ] Run `python run.py`
- [ ] Application starts without errors
- [ ] Dashboard loads correctly
- [ ] No database connection errors in logs

### Authentication Testing
- [ ] Login with super admin works
- [ ] Login with demo user works
- [ ] Password authentication works
- [ ] Google OAuth works (if configured)

### Demo User Testing
- [ ] Demo user shows 2 providers (Beget + Selectel)
- [ ] Demo user shows 7 resources
- [ ] Demo user shows 3 recommendations
- [ ] Resources display with costs
- [ ] Dashboard shows correct totals

### Admin Panel Testing
- [ ] Access admin dashboard
- [ ] View all users
- [ ] User statistics display correctly
- [ ] Click "Reseed Demo User" button
- [ ] Reseed completes successfully
- [ ] Demo user data refreshed

### Core Features Testing
- [ ] View connections page
- [ ] View resources page
- [ ] View recommendations page
- [ ] Add new cloud provider
- [ ] Edit provider credentials
- [ ] Run sync operation
- [ ] Sync completes successfully
- [ ] New resources appear

### Data Migration Verification
- [ ] All existing users present
- [ ] All provider connections migrated
- [ ] All resources migrated
- [ ] Sync history preserved
- [ ] Cost data preserved
- [ ] Recommendations migrated

## 🚀 Production Deployment (Beget)

### Phase 1: Beget MySQL Setup
- [ ] Access Beget control panel (https://cp.beget.com/)
- [ ] Create MySQL database `infrazen_prod`
- [ ] Note database credentials
- [ ] Test connection from local machine
- [ ] Configure remote access (if needed)

### Phase 2: VPS Configuration
- [ ] SSH access to Beget VPS
- [ ] Python 3.10+ installed
- [ ] Git repository cloned/uploaded
- [ ] Virtual environment created
- [ ] Dependencies installed

### Phase 3: Production Configuration
- [ ] Create `config.env.prod`
- [ ] Set `FLASK_ENV=production`
- [ ] Generate secure SECRET_KEY
- [ ] Set production DATABASE_URL
- [ ] Set production GOOGLE_CLIENT_ID
- [ ] Set appropriate LOG_LEVEL

### Phase 4: Database Initialization
- [ ] Run `python init_database.py` on VPS
- [ ] Production schema created
- [ ] Super admin created
- [ ] Demo user seeded
- [ ] Validation script passed

### Phase 5: Application Deployment
- [ ] Configure Gunicorn
- [ ] Test application start
- [ ] Configure systemd service
- [ ] Enable service auto-start
- [ ] Configure Nginx reverse proxy (optional)
- [ ] Test application access

### Phase 6: Production Validation
- [ ] Application accessible via domain/IP
- [ ] HTTPS configured (if applicable)
- [ ] Login functionality works
- [ ] Database queries execute correctly
- [ ] Provider syncs work
- [ ] No errors in application logs
- [ ] No errors in MySQL logs

## 🔒 Security & Monitoring

### Security
- [ ] Strong SECRET_KEY set
- [ ] Database credentials secured
- [ ] MySQL user has minimum required privileges
- [ ] Remote MySQL access restricted (if applicable)
- [ ] Application runs as non-root user
- [ ] Sensitive files not in web root

### Backups
- [ ] MySQL backup script created
- [ ] Backup schedule configured (cron)
- [ ] Test restore from backup
- [ ] Backup retention policy defined
- [ ] Off-site backup storage configured

### Monitoring
- [ ] Application logging configured
- [ ] MySQL slow query log enabled
- [ ] Disk space monitoring
- [ ] Database connection monitoring
- [ ] Error alerting configured

## 📚 Documentation

- [ ] Review [QUICK_START_MYSQL.md](./QUICK_START_MYSQL.md)
- [ ] Review [MYSQL_MIGRATION_GUIDE.md](./MYSQL_MIGRATION_GUIDE.md)
- [ ] Review [NEXT_STEPS.md](./NEXT_STEPS.md)
- [ ] Document custom configuration
- [ ] Document backup procedures
- [ ] Document troubleshooting steps

## 🎯 Future Enhancements

- [ ] Implement demo user deletion protection
- [ ] Add audit logging for admin actions
- [ ] Implement rate limiting on reseed
- [ ] Add database performance monitoring
- [ ] Implement query caching
- [ ] Add automated backup verification
- [ ] Set up monitoring dashboard
- [ ] Configure alerts for critical errors

## ✅ Sign-Off

### Local Development
- [ ] All local tests passed
- [ ] Demo user fully functional
- [ ] Admin reseed working
- [ ] Ready for production deployment

**Signed off by**: _________________ **Date**: _________

### Production Deployment
- [ ] All production tests passed
- [ ] Backups configured and tested
- [ ] Monitoring in place
- [ ] Documentation complete

**Signed off by**: _________________ **Date**: _________

---

## 📊 Progress Summary

**Total Items**: 90+
**Completed**: ___
**In Progress**: ___
**Blocked**: ___

**Estimated Completion**: _________

## 💡 Notes

Use this space to track issues, questions, or important observations:

```
[Date] - [Note]




```

---

**Last Updated**: ___________
**Current Phase**: ___________

