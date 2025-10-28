# ✅ Production Setup Complete

## Summary

InfraZen is fully deployed and configured on production with automated price catalog synchronization.

## Production Server

**Host:** `infrazen-prod` (217.26.28.90)  
**Domain:** https://infrazen.org  
**Application:** `/opt/infrazen`  
**Database:** Beget MySQL at `jufiedeycadeth.beget.app:3306`

## Automated Cron Jobs

### 1. Resource Sync (Daily at 8:00 AM MSK)
```bash
0 8 * * * cd /opt/infrazen && /opt/infrazen/venv/bin/python scripts/bulk_sync_all_users.py --sync-type scheduled >> /var/log/infrazen_bulk_sync.log 2>&1
```

**What it does:**
- Syncs cloud resources for all active users
- Fetches VMs, disks, networks from all connected providers
- Updates cost estimates and recommendations
- Duration: ~1 minute per user

**Log:** `/var/log/infrazen_bulk_sync.log`

### 2. Price Catalog Sync (Daily at 3:00 AM MSK)
```bash
0 3 * * * cd /opt/infrazen && /opt/infrazen/venv/bin/python scripts/sync_all_prices.py --quiet >> /var/log/infrazen_price_sync.log 2>&1
```

**What it does:**
- Syncs pricing catalogs from all enabled providers
- Beget: 216 SKUs (~10 seconds)
- Selectel: 4,109 SKUs (~47 seconds)
- Yandex Cloud: 993 SKUs (~5-6 minutes)
- Total: 5,318 SKUs in ~6-7 minutes

**Log:** `/var/log/infrazen_price_sync.log`

## Configuration System

### Development (Local Mac)
- **File:** `config.dev.env` (Git ignored)
- **Database:** Local MySQL `localhost:3306/infrazen_dev`
- **Purpose:** Local development and testing

### Production (Server)
- **File:** `config.prod.env` (Git ignored)
- **Database:** Beget MySQL `jufiedeycadeth.beget.app:3306/infrazen_prod`
- **Purpose:** Production deployment

### Template
- **File:** `config.example.env` (Git tracked)
- **Purpose:** Template to copy and fill in

## Deployment

### Manual Deployment

```bash
ssh infrazen-prod
cd /opt/infrazen
sudo ./deploy
```

**What it does:**
1. Pulls latest code from GitHub
2. Installs/updates Python dependencies
3. Runs database migrations
4. Restarts the service (zero-downtime)
5. Health check
6. Reports success/failure

### Automatic Git Pull (if needed)

```bash
ssh infrazen-prod
cd /opt/infrazen
git pull
sudo systemctl restart infrazen
```

**Note:** The `deploy` script is recommended as it includes health checks and migrations.

## Manual Script Execution

Both scripts can be run manually via SSH:

### Test Resource Sync

```bash
ssh infrazen-prod
cd /opt/infrazen
venv/bin/python scripts/bulk_sync_all_users.py --sync-type manual --verbose
```

### Test Price Sync

```bash
ssh infrazen-prod
cd /opt/infrazen
venv/bin/python scripts/sync_all_prices.py --verbose
```

**Note:** Scripts automatically use `config.prod.env` on production.

## Production Database

**Connection Details:**
- **Host:** `jufiedeycadeth.beget.app:3306`
- **User:** `infrazen_prod`
- **Database:** `infrazen_prod`
- **Password:** (stored in `config.prod.env`)
- **Access from:** `217.26.28.90` (production server IP)

**Tables:**
- `users` - User accounts
- `cloud_providers` - User provider connections
- `resources` - Cloud resources (VMs, disks, etc.)
- `provider_prices` - Pricing catalog (5,318+ SKUs)
- `provider_catalog` - Provider metadata
- `sync_snapshots` - Sync history
- `complete_syncs` - Bulk sync tracking
- `optimization_recommendations` - Cost optimization suggestions
- `price_comparison_recommendations` - Cross-provider price comparisons

## Monitoring

### Check Service Status

```bash
ssh infrazen-prod
sudo systemctl status infrazen
```

### View Application Logs

```bash
# Last 100 lines
sudo journalctl -u infrazen -n 100

# Follow live
sudo journalctl -u infrazen -f
```

### Check Cron Logs

```bash
# Resource sync log
sudo tail -100 /var/log/infrazen_bulk_sync.log

# Price sync log
sudo tail -100 /var/log/infrazen_price_sync.log
```

### Database Queries

```bash
ssh infrazen-prod
cd /opt/infrazen
venv/bin/python -c "
from app import create_app
from app.core.models.pricing import ProviderPrice
from app.core.models.provider_catalog import ProviderCatalog

app = create_app()
with app.app_context():
    # Check price counts
    providers = ProviderCatalog.query.filter_by(is_enabled=True).all()
    for p in providers:
        count = ProviderPrice.query.filter_by(provider=p.provider_type).count()
        print(f'{p.display_name}: {count} SKUs, last sync: {p.last_price_sync}')
"
```

## Key Features Implemented

### Price Sync Improvements
- ✅ Individual SKU fetching for Yandex (993 SKUs vs 118 before)
- ✅ Database reconnection for long-running syncs
- ✅ Batch commits every 100 records
- ✅ UPSERT instead of DELETE (preserves recommendations)
- ✅ Progress tracking and logging
- ✅ Exit codes for cron monitoring

### Config Improvements
- ✅ Clear naming: `config.dev.env` and `config.prod.env`
- ✅ Auto-detection based on file existence
- ✅ All configs git-ignored (except template)
- ✅ Production secrets never in Git
- ✅ Deploy script preserves production config

### Production Readiness
- ✅ Zero-downtime deployments
- ✅ Health checks
- ✅ Automated daily syncs
- ✅ Comprehensive logging
- ✅ Error handling and recovery

## Performance Metrics

### Resource Sync (8:00 AM daily)
- **Users:** 6 total (2 active, 4 skipped)
- **Duration:** ~46 seconds
- **Resources:** 16 cloud resources discovered
- **Recommendations:** Generated for cost savings

### Price Sync (3:00 AM daily)
- **Providers:** 3 (Beget, Selectel, Yandex)
- **Duration:** ~6-7 minutes total
- **SKUs:** 5,318 pricing records
- **Success Rate:** 100%

## Troubleshooting

### Scripts fail with "Can't connect to database"
- **Check:** `config.prod.env` exists with correct DATABASE_URL
- **Fix:** Ensure `jufiedeycadeth.beget.app` is reachable

### Cron job doesn't run
- **Check:** `sudo -u infrazen crontab -l`
- **Verify:** Logs in `/var/log/infrazen_*.log`

### Deploy fails
- **Check:** `config.prod.env` exists
- **Check:** Git pull succeeds
- **View logs:** `sudo journalctl -u infrazen -n 100`

## Next Steps

- ✅ Monitor tomorrow's scheduled syncs (3:00 AM price, 8:00 AM resources)
- ✅ Check logs for any errors
- ✅ Verify pricing data in admin panel

## Completed Setup Checklist

- [x] Clean config system implemented
- [x] Production config created (`config.prod.env`)
- [x] Development config created (`config.dev.env`)
- [x] Deploy script updated and tested
- [x] Systemd service configured
- [x] Price sync script tested (all 3 providers)
- [x] Bulk sync script tested
- [x] Cron jobs configured
- [x] Log files created
- [x] Database reconnection logic added
- [x] Batch commits implemented
- [x] Production deployment verified
- [x] All scripts working

**🚀 Production is fully operational and automated!**

