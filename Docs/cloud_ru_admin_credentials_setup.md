# Cloud.ru Admin Credentials Setup

## Overview

Cloud.ru pricing sync requires admin credentials to be configured. These credentials are used by the system to fetch pricing data for all users.

## Setup Methods

### Method 1: Admin UI (Recommended)

1. **Access Admin Panel**: Navigate to `/admin/providers`
2. **Find Cloud.ru**: Locate Cloud.ru in the providers list
3. **Click Credentials Button**: Click the "Credentials" button for Cloud.ru
4. **Enter Credentials**:
   - **Key ID**: Your Cloud.ru service account Key ID
   - **Key Secret**: Your Cloud.ru service account Key Secret
5. **Test Connection**: Click "Test Connection" to verify credentials
6. **Save**: Click "Save" to store credentials

### Method 2: Admin API

```bash
POST /api/admin/providers/cloud-ru/credentials
Content-Type: application/json

{
  "credential_type": "basic_auth",
  "credentials": {
    "api_key": "your_key_id",
    "api_secret": "your_key_secret"
  },
  "description": "Cloud.ru pricing sync credentials",
  "is_active": true
}
```

### Method 3: Migration Script (Optional)

A migration script is available at:
- `migrations/versions/add_cloud_ru_admin_credentials.py`

This creates an **inactive placeholder**. You must still configure actual credentials via Admin UI or API.

**Note**: The migration creates an inactive placeholder. You must activate and configure it manually.

## Credential Requirements

- **Key ID**: Service account Key ID from Cloud.ru console
- **Key Secret**: Service account Key Secret from Cloud.ru console
- **Service Account**: Must have permissions to:
  - Access pricing APIs
  - Read project information
  - Fetch flavors and pricing data

## Verification

After setting up credentials:

1. **Test via Admin UI**: Use the "Test Connection" button
2. **Test via API**: 
   ```bash
   POST /api/admin/providers/cloud-ru/credentials/test-raw
   {
     "api_key": "your_key_id",
     "api_secret": "your_key_secret"
   }
   ```
3. **Test Pricing Sync**:
   ```bash
   POST /api/admin/providers/<provider_id>/sync-prices
   ```

## Troubleshooting

### Credentials Not Working

1. **Verify Key ID and Secret**: Ensure they match your Cloud.ru service account
2. **Check Permissions**: Service account must have access to pricing APIs
3. **Check Project ID**: The project_id is extracted from the JWT token automatically
4. **Review Logs**: Check application logs for authentication errors

### Pricing Sync Fails

1. **Check Admin Credentials**: Ensure they're configured and active
2. **Verify Provider Status**: Cloud.ru must be enabled in ProviderCatalog
3. **Check has_pricing_api**: Must be `True` for Cloud.ru
4. **Review Error Messages**: Check sync error in ProviderCatalog

## Security Notes

- Admin credentials are stored encrypted in the database
- Credentials are only accessible to admin users
- Never commit credentials to version control
- Rotate credentials periodically for security

## Related Files

- `app/core/models/provider_admin_credentials.py` - Credentials model
- `app/api/admin.py` - Admin API endpoints
- `app/templates/admin/providers.html` - Admin UI
- `app/providers/cloud_ru/pricing_client.py` - Pricing client implementation

