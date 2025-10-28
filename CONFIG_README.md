# Configuration Management

## Clear and Simple Config System

InfraZen uses **two config files**, both git-ignored:

| File | Environment | Location | Git Tracked |
|------|-------------|----------|-------------|
| `config.dev.env` | **Development** (your Mac) | `/Users/.../InfraZen/` | ❌ No |
| `config.prod.env` | **Production** (server) | `/opt/infrazen/` | ❌ No |
| `config.example.env` | **Template** (copy this) | Both | ✅ Yes |

## How It Works

```python
# app/config.py automatically loads:
if os.path.exists('config.prod.env'):
    load_dotenv('config.prod.env')  # Production
else:
    load_dotenv('config.dev.env')  # Development
```

**Simple rule:** 
- Has `config.prod.env`? → Production mode
- No `config.prod.env`? → Development mode (uses `config.dev.env`)

## Setup Instructions

### Local Development Setup

```bash
# 1. Clone repo
git clone https://github.com/colaisr/infrazen.git
cd infrazen

# 2. Copy template
cp config.example.env config.dev.env

# 3. Edit with your local settings
nano config.dev.env

# Set:
# - DATABASE_URL=mysql+pymysql://infrazen_user:infrazen_password@localhost:3306/infrazen_dev
# - FLASK_ENV=development
```

### Production Setup

```bash
# 1. SSH to server
ssh infrazen-prod
cd /opt/infrazen

# 2. Copy template
cp config.example.env config.prod.env

# 3. Edit with production settings
sudo nano config.prod.env

# Set:
# - DATABASE_URL=mysql+pymysql://infrazen_prod:PASSWORD@jufiedeycadeth.beget.app:3306/infrazen_prod
# - FLASK_ENV=production
# - SECRET_KEY=<generate-secure-key>
# - MAIL credentials for registration@infrazen.ru
```

## Production Database

**Host:** `jufiedeycadeth.beget.app:3306`  
**Access from:** `217.26.28.90` (production server IP)  
**User:** `infrazen_prod`  
**Database:** `infrazen_prod`

## File Contents

### config.dev.env (Local)
```bash
FLASK_ENV=development
DATABASE_URL=mysql+pymysql://infrazen_user:infrazen_password@localhost:3306/infrazen_dev?charset=utf8mb4
GOOGLE_CLIENT_ID=your-dev-client-id
# ... other dev settings
```

### config.prod.env (Production)
```bash
FLASK_ENV=production
DATABASE_URL=mysql+pymysql://infrazen_prod:Kok5489103!@jufiedeycadeth.beget.app:3306/infrazen_prod?charset=utf8mb4
GOOGLE_CLIENT_ID=421154810757-i7ssn34msfpqlf0s5fkfrucun5sgut4d.apps.googleusercontent.com
SECRET_KEY=infrazen-finops-secret-key-2025
MAIL_USERNAME=registration@infrazen.ru
# ... other prod settings
```

## Systemd Service

The production systemd service loads `config.prod.env`:

```ini
[Service]
EnvironmentFile=/opt/infrazen/config.prod.env
```

## Deploy Script

The `/opt/infrazen/deploy` script should:

1. Pull latest code from Git
2. **NOT touch config.prod.env** (it's not in Git)
3. Restart the service

```bash
#!/bin/bash
cd /opt/infrazen
git pull
sudo systemctl restart infrazen
echo "✅ Deployed successfully"
```

## Scripts (bulk_sync, price_sync)

All scripts automatically use the correct config:

- **Local:** Uses `config.dev.env` → local MySQL
- **Production:** Uses `config.prod.env` → Beget MySQL

No changes needed between environments!

## Security

- ❌ **Never commit** `config.dev.env` or `config.prod.env`
- ✅ **Always commit** `config.example.env` (template only)
- ✅ Git automatically ignores both dev and prod configs
- 🔒 Production secrets stay only on server

## Migration from Old System

If you have old files:

**On local Mac:**
```bash
mv config.env config.dev.env
# OR copy from example:
cp config.example.env config.dev.env
nano config.dev.env
```

**On production:**
```bash
ssh infrazen-prod
cd /opt/infrazen
sudo mv config.env.local config.prod.env
# OR if you have config.env with prod settings:
sudo mv config.env config.prod.env
```

## What's in Git vs What's Not

**In Git (safe templates):**
- ✅ `config.example.env` - Template to copy
- ✅ `CONFIG_README.md` - This documentation

**NOT in Git (real secrets):**
- ❌ `config.dev.env` - Your local dev config
- ❌ `config.prod.env` - Production config with real passwords

## Troubleshooting

### "App can't connect to database"

**Check which config is loaded:**
```python
python -c "
import os
if os.path.exists('config.prod.env'):
    print('Using: config.prod.env (PRODUCTION)')
else:
    print('Using: config.dev.env (DEVELOPMENT)')
"
```

### "Config file not found"

Create the appropriate file:
```bash
# Local:
cp config.example.env config.dev.env

# Production:
sudo cp config.example.env config.prod.env
sudo nano config.prod.env  # Add real credentials
```

## Summary

✅ **Clear naming:** `dev` = local, `prod` = server  
✅ **No mix:** Production ONLY uses `config.prod.env`  
✅ **All excluded from Git:** Both configs are git-ignored  
✅ **Deploy script safe:** Git pull won't overwrite configs  
✅ **Scripts work:** Auto-detect environment, no changes needed
