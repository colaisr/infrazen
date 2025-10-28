# Price Sync Cron Job Setup

## Overview

This document describes how to set up automated price catalog synchronization for all enabled cloud providers using cron scheduling.

## Script

The script `scripts/sync_all_prices.py` synchronizes pricing catalogs from all enabled cloud providers that have a pricing API (Yandex Cloud, Selectel, Beget).

### Features

- **Standalone execution**: Runs in Flask app context without UI or authentication
- **Flexible scheduling**: Can sync all providers or a specific one
- **Multiple output modes**: Normal, verbose, quiet, dry-run
- **Exit codes**: Proper exit codes for cron monitoring
  - `0`: All providers synced successfully
  - `1`: All providers failed
  - `2`: Some providers failed (partial success)
  - `130`: Interrupted by user
- **Logging**: Detailed console output and progress tracking
- **Production-ready**: Tested locally and designed for production deployment

### Usage

```bash
# Sync all providers (default)
python scripts/sync_all_prices.py

# Sync only Yandex Cloud
python scripts/sync_all_prices.py --provider yandex

# Dry run to see what would be synced
python scripts/sync_all_prices.py --dry-run

# Verbose output
python scripts/sync_all_prices.py --verbose

# Quiet mode (only errors and summary)
python scripts/sync_all_prices.py --quiet
```

## Cron Job Setup

### Recommended Schedule

Price catalogs should be synced **once daily** at off-peak hours. Recommended time: **3:00 AM**.

### Installation Steps

1. **Log in to production server** as the `infrazen` user:
   ```bash
   sudo -u infrazen crontab -e
   ```

2. **Add the following cron entry**:
   ```cron
   # Price catalog sync - Daily at 3:00 AM
   0 3 * * * cd /opt/infrazen && /opt/infrazen/venv/bin/python scripts/sync_all_prices.py --quiet >> /var/log/infrazen_price_sync.log 2>&1
   ```

3. **Save and exit** the crontab editor

4. **Verify the cron job** is installed:
   ```bash
   sudo -u infrazen crontab -l | grep price_sync
   ```

### Log File

The sync output is logged to `/var/log/infrazen_price_sync.log`. Monitor this file for:
- Sync success/failure
- Number of SKUs synced per provider
- Duration and performance metrics
- Any errors or warnings

```bash
# View recent sync logs
sudo tail -100 /var/log/infrazen_price_sync.log

# Monitor live during sync
sudo tail -f /var/log/infrazen_price_sync.log
```

## Sync Performance

Based on local testing:

| Provider | Typical Duration | Typical SKU Count |
|----------|------------------|-------------------|
| Yandex Cloud | 6-7 minutes | ~993 SKUs |
| Selectel | ~5 seconds | ~50 SKUs |
| Beget | ~5 seconds | ~30 SKUs |
| **Total** | **~7 minutes** | **~1,070 SKUs** |

## Testing

### Local Testing

```bash
# Test dry-run
python scripts/sync_all_prices.py --dry-run

# Test actual sync
python scripts/sync_all_prices.py --verbose
```

### Production Testing

**Note**: The script requires the database to be running. On production, MySQL/MariaDB may not be accessible outside of scheduled cron execution times or when the Flask application is running.

To test on production:
```bash
# As infrazen user, during application runtime
cd /opt/infrazen
/opt/infrazen/venv/bin/python scripts/sync_all_prices.py --verbose
```

## Integration with Existing Cron Jobs

The price sync cron job complements the existing resource sync:

```cron
# Resource sync - Daily at 8:00 AM
0 8 * * * cd /opt/infrazen && /opt/infrazen/venv/bin/python scripts/bulk_sync_all_users.py --sync-type scheduled >> /var/log/infrazen_bulk_sync.log 2>&1

# Price catalog sync - Daily at 3:00 AM
0 3 * * * cd /opt/infrazen && /opt/infrazen/venv/bin/python scripts/sync_all_prices.py --quiet >> /var/log/infrazen_price_sync.log 2>&1
```

**Why 3:00 AM for price sync?**
- Off-peak hours (minimal user activity)
- Runs before the 8:00 AM resource sync
- Ensures fresh pricing data for the daily resource sync
- Yandex Cloud pricing updates typically happen overnight

## Admin Panel Integration

In addition to the cron job, the admin panel provides a UI for manual price sync:

1. Navigate to **Admin Panel** → **Providers**
2. Click **"Sync Prices"** for a specific provider
3. Or use the **"Sync All Prices"** button (via `/api/admin/sync-all-prices` endpoint)

**Note**: Yandex Cloud sync in the admin panel runs in a background thread to prevent UI timeouts due to the 6-7 minute sync duration.

## Monitoring

### Success Indicators

- Exit code `0`
- Log contains: `Price sync completed: X successful, 0 failed`
- Database `provider_catalog.last_price_sync` updated
- Database `provider_catalog.sync_status` = `'success'`
- Database `provider_prices` table has ~1,070 records for enabled providers

### Failure Indicators

- Exit code `1` or `2`
- Log contains error messages
- Database `provider_catalog.sync_error` contains error details
- Database `provider_catalog.sync_status` = `'failed'`

### Query to Check Last Sync

```sql
SELECT 
    provider_type,
    display_name,
    last_price_sync,
    sync_status,
    sync_error,
    (SELECT COUNT(*) FROM provider_prices WHERE provider = provider_catalog.provider_type) as price_count
FROM provider_catalog
WHERE has_pricing_api = 1 AND is_enabled = 1;
```

## Troubleshooting

### Script Fails with Database Connection Error

**Symptom**: `(pymysql.err.OperationalError) (2003, "Can't connect to MySQL server on 'localhost' ([Errno 111] Connection refused")`

**Cause**: MySQL/MariaDB service not running

**Solution**: 
- Check if the web application is running: `sudo systemctl status infrazen`
- The database should be accessible during normal application runtime
- The cron job will work if scheduled during hours when the application is active
- For manual testing, ensure the infrazen service is running

### Yandex Cloud Sync Times Out

**Symptom**: Sync takes longer than expected or appears hung

**Cause**: Yandex Cloud has ~1,150 SKUs and fetches each individually

**Solution**:
- Normal behavior; Yandex sync takes 6-10 minutes
- The script has a 20-minute timeout built-in
- Use `--verbose` flag to monitor progress
- Check logs for "Progress: X SKUs with prices" messages every 50 SKUs

### Zero SKUs Synced

**Symptom**: Sync completes but `records_synced` is 0

**Cause**: Provider credentials missing or invalid

**Solution**:
- Check admin panel for provider credentials
- Verify credentials work by testing in admin panel
- Check provider logs for authentication errors

## Future Enhancements

- **Email notifications** on sync failures
- **Prometheus metrics** for monitoring
- **Differential sync** (only update changed prices)
- **Historical price tracking** and trend analysis
- **Automatic price anomaly detection**

## Related Documentation

- `scripts/bulk_sync_all_users.py` - Resource synchronization script
- `app/api/admin.py` - Admin API endpoints including price sync
- `app/core/services/price_update_service.py` - Price sync service logic
- `app/providers/plugins/yandex.py` - Yandex Cloud pricing implementation

