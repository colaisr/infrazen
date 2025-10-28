# Configuration Management

## Overview

InfraZen uses a simple, clean two-file configuration approach:

- **`config.env`** - Development configuration (Git tracked)
- **`config.env.local`** - Production configuration (Git ignored, SSH managed)

## How It Works

The application automatically loads the correct config:

```python
if os.path.exists('config.env.local'):
    load_dotenv('config.env.local')  # Production
else:
    load_dotenv('config.env')  # Development
```

**Priority:** `config.env.local` > `config.env`

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/colaisr/infrazen.git
   cd infrazen
   ```

2. **Use the default `config.env`**
   - Already tracked in Git
   - Contains safe development defaults
   - Uses local MySQL: `localhost:3306/infrazen_dev`

3. **Optional: Override locally**
   ```bash
   cp config.env config.env.local
   # Edit config.env.local with your local settings
   ```

## Production Setup

1. **SSH into production server**
   ```bash
   ssh infrazen-prod
   cd /opt/infrazen
   ```

2. **Create `config.env.local` with production credentials**
   ```bash
   sudo nano config.env.local
   ```

3. **Add production settings:**
   ```bash
   # InfraZen Production Configuration
   
   FLASK_ENV=production
   SECRET_KEY=<generate-secure-key>
   
   # Production Database
   DATABASE_URL=mysql+pymysql://user:password@10.19.0.1:3306/infrazen_prod?charset=utf8mb4
   
   # Google OAuth
   GOOGLE_CLIENT_ID=<your-prod-client-id>.apps.googleusercontent.com
   
   # Email (Beget SMTP)
   MAIL_SERVER=smtp.beget.com
   MAIL_PORT=465
   MAIL_USE_SSL=True
   MAIL_USE_TLS=False
   MAIL_USERNAME=registration@infrazen.ru
   MAIL_PASSWORD=<your-mail-password>
   MAIL_DEFAULT_SENDER=registration@infrazen.ru
   
   # Logging
   LOG_LEVEL=INFO
   ```

4. **Restart the application**
   ```bash
   sudo systemctl restart infrazen
   ```

## File Structure

```
infrazen/
├── config.env              # Development (Git tracked)
├── config.env.local        # Production (Git ignored)
├── CONFIG_README.md        # This file
└── .gitignore             # Ignores config.env.local
```

## Security

- ✅ `config.env` - Safe to commit (no secrets)
- ❌ `config.env.local` - **NEVER commit** (contains secrets)
- ✅ Git automatically ignores `config.env.local`

## Scripts and Cron Jobs

All scripts (`bulk_sync_all_users.py`, `sync_all_prices.py`) automatically use the correct config:

- **Development:** Uses `config.env` (local MySQL)
- **Production:** Uses `config.env.local` (production MySQL)

No code changes needed between environments!

## Common Issues

### "Can't connect to database"

**Development:**
- Ensure MySQL is running locally
- Check credentials in `config.env`

**Production:**
- Ensure `config.env.local` exists
- Verify DATABASE_URL points to correct server
- Check MySQL server is accessible

### "Script works locally but not on production"

1. Verify `config.env.local` exists on production
2. Check DATABASE_URL in `config.env.local`
3. Test connectivity: `mysql -h 10.19.0.1 -u user -p`

## Migration from Old Config

If you have old config files (`config.env.example`, `config.env.prod`):

1. **On production:** Rename to `config.env.local`
   ```bash
   sudo mv /opt/infrazen/config.env.prod /opt/infrazen/config.env.local
   ```

2. **Remove old files from git:**
   ```bash
   git rm config.env.example config.env.prod config.env.dev
   ```

## Systemd Service

The systemd service loads environment from the config file:

```ini
[Service]
EnvironmentFile=/opt/infrazen/config.env
```

**Note:** This should be updated to check for `config.env.local` first, but since our app code handles the priority, it works either way.

## Best Practices

1. ✅ Keep `config.env` with safe defaults
2. ✅ Create `config.env.local` on production only
3. ✅ Never commit `config.env.local`
4. ✅ Backup `config.env.local` separately (not in Git)
5. ✅ Use strong passwords and keys in production

## Quick Reference

| File | Environment | Git Tracked | Contains Secrets |
|------|-------------|-------------|------------------|
| `config.env` | Development | ✅ Yes | ❌ No |
| `config.env.local` | Production | ❌ No | ✅ Yes |

