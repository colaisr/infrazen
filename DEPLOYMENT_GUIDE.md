# InfraZen Deployment Guide

## 🔐 Credentials Management

### Development Environment
Credentials are stored in `config.env` file which is **excluded from Git** (listed in `.gitignore`).

**Current setup:**
```bash
# File: config.env (NOT committed to Git)
MAIL_SERVER=smtp.beget.com
MAIL_PORT=465
MAIL_USE_SSL=True
MAIL_USE_TLS=False
MAIL_USERNAME=registration@infrazen.ru
MAIL_PASSWORD=Kok5489103!!
MAIL_DEFAULT_SENDER=registration@infrazen.ru
```

### ✅ Security Status
- ✅ `config.env` is in `.gitignore` (line 45)
- ✅ Passwords are NOT committed to Git
- ✅ Template files (`config.env.example`, `config.env.prod`) are safe to commit
- ✅ Production credentials stored separately

---

## 🚀 Production Deployment (Beget VPS)

### Option 1: Manual Configuration (Recommended)

**Step 1:** On production server, create `config.env`:
```bash
cd /path/to/infrazen
nano config.env
```

**Step 2:** Add production configuration:
```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=<generate-secure-key>  # Run: python -c "import secrets; print(secrets.token_hex(32))"

# Database Configuration - Beget MySQL
DATABASE_URL=mysql+pymysql://your_user:your_password@mysql.beget.com:3306/infrazen_prod?charset=utf8mb4

# Google OAuth
GOOGLE_CLIENT_ID=your-production-google-client-id.apps.googleusercontent.com

# Email Configuration (Beget SMTP)
MAIL_SERVER=smtp.beget.com
MAIL_PORT=465
MAIL_USE_SSL=True
MAIL_USE_TLS=False
MAIL_USERNAME=registration@infrazen.ru
MAIL_PASSWORD=Kok5489103!!
MAIL_DEFAULT_SENDER=registration@infrazen.ru

# Logging
LOG_LEVEL=INFO
```

**Step 3:** Set proper permissions:
```bash
chmod 600 config.env  # Only owner can read/write
```

### Option 2: Use config.env.prod Template

**Step 1:** Copy template to production:
```bash
scp config.env.prod user@your-server:/path/to/infrazen/config.env
```

**Step 2:** Edit on server:
```bash
ssh user@your-server
cd /path/to/infrazen
nano config.env  # Update DATABASE_URL and SECRET_KEY
chmod 600 config.env
```

---

## 🔒 Environment Variables Loading

The app loads configuration in this order:

1. **Environment variables** (highest priority)
2. **config.env file** (loaded by `python-dotenv`)
3. **Default values** (in `app/config.py`)

### How it works:
```python
# app/config.py
from dotenv import load_dotenv
load_dotenv('config.env')  # Loads config.env into environment

class Config:
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')  # Gets from environment
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
```

---

## 📋 Pre-Deployment Checklist

### Before committing:
- [ ] ✅ `config.env` is in `.gitignore`
- [ ] ✅ No passwords in Git history
- [ ] ✅ `config.env.example` updated with placeholders
- [ ] ✅ `config.env.prod` updated (but with placeholders for sensitive data)

### On production server:
- [ ] Create `config.env` manually
- [ ] Set `chmod 600 config.env`
- [ ] Generate new `SECRET_KEY` for production
- [ ] Update `DATABASE_URL` with production MySQL credentials
- [ ] Update `GOOGLE_CLIENT_ID` with production OAuth credentials
- [ ] Verify email credentials (MAIL_USERNAME, MAIL_PASSWORD)
- [ ] Run database migrations: `alembic upgrade head`
- [ ] Test email sending

---

## 🔄 Deployment Script Example

```bash
#!/bin/bash
# deploy.sh - Production deployment script

# 1. Pull latest code
cd /path/to/infrazen
git pull origin master

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install/update dependencies
pip install -r requirements.txt

# 4. Run database migrations
alembic upgrade head

# 5. Restart application
# For systemd:
sudo systemctl restart infrazen

# For PM2:
pm2 restart infrazen

# For manual:
# pkill -f "python run.py"
# nohup python run.py > /dev/null 2>&1 &
```

---

## 🛡️ Security Best Practices

### 1. **Never commit `config.env`**
```bash
# Check what will be committed:
git status

# If config.env appears, reset it:
git reset config.env
```

### 2. **Rotate passwords regularly**
- Change `MAIL_PASSWORD` every 3-6 months
- Update `SECRET_KEY` if compromised

### 3. **Use environment-specific configs**
```bash
# Development
config.env → used locally

# Production
config.env → created manually on server
```

### 4. **Restrict file permissions**
```bash
# Production server
chmod 600 config.env        # Only owner can read/write
chown www-data:www-data config.env  # Set proper owner
```

---

## 📧 Testing Email Configuration

### On production server:

```python
# test_email.py
from app.core.services.email_service import EmailService
from flask import Flask

app = Flask(__name__)
app.config.from_object('app.config.ProductionConfig')

with app.app_context():
    success = EmailService.send_email(
        to_email='your-test-email@example.com',
        subject='InfraZen Test',
        body_html='<p>Test email from production</p>',
        body_text='Test email from production'
    )
    print(f"Email sent: {success}")
```

Run test:
```bash
python test_email.py
```

---

## 🔍 Troubleshooting

### Email not sending?

1. **Check credentials:**
   ```bash
   grep MAIL_ config.env
   ```

2. **Test SMTP connection:**
   ```bash
   telnet smtp.beget.com 465
   ```

3. **Check logs:**
   ```bash
   tail -f server.log | grep email_service
   ```

4. **Verify mailbox exists:**
   - Login to Beget control panel
   - Check Mail → Mailboxes
   - Verify `registration@infrazen.ru` exists

### Common issues:

| Error | Solution |
|-------|----------|
| "Authentication failed" | Check MAIL_USERNAME and MAIL_PASSWORD |
| "Connection timeout" | Check MAIL_PORT (465 for SSL) |
| "Certificate error" | Ensure MAIL_USE_SSL=True |
| "Email not found" | Create mailbox in Beget control panel |

---

## 📝 What Gets Committed to Git

✅ **Safe to commit:**
- `config.env.example` (template with placeholders)
- `config.env.prod` (template with placeholders)
- `app/config.py` (code that loads environment variables)
- `DEPLOYMENT_GUIDE.md` (this file)

❌ **NEVER commit:**
- `config.env` (contains actual passwords)
- Any file with real credentials
- Database backups with user data
- SSH keys or certificates

---

## 🎯 Quick Reference

```bash
# Local development
cp config.env.example config.env
nano config.env  # Add your credentials
./venv/bin/python run.py

# Production deployment
ssh user@your-server
cd /path/to/infrazen
git pull origin master
nano config.env  # Create/update with production credentials
chmod 600 config.env
alembic upgrade head
sudo systemctl restart infrazen
```

---

---

## ⏱️ Nginx Timeout for Complete Sync

Full sync ("Обновить все") can take 5–10+ minutes (Cloud.ru 600+ resources + recommendations). Default nginx `proxy_read_timeout` (~60s) causes 504.

**Add this location block** before `location /` in `/etc/nginx/sites-available/infrazen`:

```nginx
    location /api/complete-sync {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    proxy_read_timeout 600s;
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    }
```

Then:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Reference: `deploy/nginx-complete-sync.conf`

---

## 📞 Support

If you need to change email credentials:
1. Update mailbox password in Beget control panel
2. Update `MAIL_PASSWORD` in `config.env` on production server
3. Restart the application

**Beget Control Panel:** https://beget.com/ru/panel
**Email Settings:** Mail → Mailboxes → registration@infrazen.ru



















