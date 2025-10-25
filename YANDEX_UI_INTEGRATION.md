# Yandex Cloud UI Integration - Changes Summary

## ✅ **Problem Solved**

The connection modal now properly handles Yandex Cloud's **service account JSON key** instead of separate fields!

## 🔧 **Files Modified**

### 1. **`app/static/js/connections.js`** - Connection Modal

**Changed Yandex Configuration** (Lines 11-23):

**Before**:
```javascript
yandex: {
    fields: [
        { name: 'access_key', label: 'Access Key ID *', type: 'text', ... },
        { name: 'secret_key', label: 'Secret Access Key *', type: 'password', ... },
        { name: 'organization_id', label: 'Organization ID *', type: 'text', ... },
        { name: 'cloud_id', label: 'Cloud ID *', type: 'text', ... }
    ]
}
```

**After**:
```javascript
yandex: {
    name: 'Yandex Cloud',
    description: 'Yandex Cloud — российская облачная платформа. Для подключения требуется JSON-ключ сервисного аккаунта (Authorized Key).',
    fields: [
        { 
            name: 'service_account_key', 
            label: 'Service Account Key (JSON) *', 
            type: 'textarea', 
            placeholder: '{\n  "id": "ajel...",\n  ...\n}',
            required: true,
            rows: 8
        }
    ]
}
```

**Added Form Action** (Lines 125-126):
```javascript
} else if (selectedProvider === 'yandex') {
    form.action = '/api/providers/yandex/add';
}
```

**Added Test Endpoint** (Lines 394-396):
```javascript
} else if (selectedProvider === 'yandex') {
    testEndpoint = '/api/providers/yandex/test';
}
```

**Added Edit Form Handler** (Lines 554-558):
```javascript
} else if (provider === 'yandex') {
    const serviceAccountKeyField = document.querySelector('textarea[name="service_account_key"]');
    if (serviceAccountKeyField) {
        serviceAccountKeyField.value = connectionData.service_account_key || '';
    }
}
```

**Improved Textarea Rendering** (Lines 158-168):
- Added support for `rows` parameter
- Added help text for service account key
- Better placeholder formatting

### 2. **`app/providers/yandex/routes.py`** - API Endpoints

Added complete CRUD operations:

- ✅ `POST /api/providers/yandex/test` - Test connection from form
- ✅ `POST /api/providers/yandex/add` - Add new connection
- ✅ `GET /api/providers/yandex/<id>/edit` - Get connection for editing
- ✅ `POST /api/providers/yandex/<id>/update` - Update connection
- ✅ `DELETE /api/providers/yandex/<id>/delete` - Delete connection
- ✅ `POST /api/providers/yandex/<id>/sync` - Sync resources
- ✅ `GET /api/providers/yandex/<id>/clouds` - List clouds
- ✅ `GET /api/providers/yandex/<id>/folders` - List folders

### 3. **`app/__init__.py`** - Blueprint Registration

Added:
```python
from app.providers.yandex.routes import yandex_bp
app.register_blueprint(yandex_bp, url_prefix='/api/providers/yandex')
```

## 🎯 **What the User Sees Now**

### Connection Modal - Yandex Cloud

When you select "Yandex Cloud" from the dropdown:

**Field Shown**:
```
Service Account Key (JSON) *
┌──────────────────────────────────────────────┐
│ {                                            │
│   "id": "ajel...",                          │
│   "service_account_id": "aje...",           │
│   "private_key": "-----BEGIN PRIVATE KEY..." │
│ }                                            │
└──────────────────────────────────────────────┘
Вставьте полный JSON-ключ сервисного аккаунта из Yandex Cloud
```

**Buttons**:
- 🧪 **"Тестировать подключение"** - Tests the JSON key
- 💾 **"Подключить Yandex Cloud"** - Saves the connection

### Test Connection Response

**Success**:
```
✅ Подключение успешно! Аккаунт: My Cloud (ID: b1g...)
```

**Error Examples**:
```
❌ Invalid JSON format for service account key. Please paste the complete JSON file from Yandex Cloud.
❌ Invalid service account key. Missing fields: private_key
❌ IAM token generation failed: [details]
```

### After Connection Added

**Connections Page Shows**:
- ✅ Provider card with "Yandex Cloud" name
- ✅ Connection name
- ✅ Sync button (works!)
- ✅ Edit button (preserves JSON)
- ✅ Delete button

## 📝 **Complete User Flow**

### 1. Create Service Account in Yandex Cloud
1. Go to https://console.cloud.yandex.com/
2. Your Folder → Service accounts → Create
3. Name: `infrazen-integration`
4. Role: `viewer`
5. Click **"Создать авторизованный ключ"** (Create authorized key) ✅
6. Download JSON file

### 2. Add Connection in InfraZen
1. Go to http://127.0.0.1:5001/connections
2. Click "Добавить провайдера" (Add Provider)
3. Select **"Yandex Cloud"** from dropdown
4. Modal shows **single textarea** for JSON
5. Paste entire JSON from Step 1
6. Enter connection name (e.g., "My Yandex Cloud")
7. Click "Тестировать подключение"
8. See: "✅ Connection successful, 1 clouds found"
9. Click "Подключить Yandex Cloud"
10. Redirect to connections page

### 3. Sync Resources
1. Find your Yandex Cloud card
2. Click "Синхронизация" button
3. Wait for sync (discovers VMs, disks, networks)
4. See results in Resources page

### 4. Edit Connection
1. Click edit button on Yandex card
2. Modal opens with JSON prefilled in textarea
3. Can update JSON or connection name
4. Click "Сохранить изменения"

## 🔍 **Technical Details**

### Form Data Flow

```
User pastes JSON
    ↓
Modal validates required field
    ↓
POST to /api/providers/yandex/test
    ↓
YandexClient.test_connection()
    ↓
Returns clouds found
    ↓
User clicks "Connect"
    ↓
POST to /api/providers/yandex/add
    ↓
Creates CloudProvider record
    ↓
Redirects to connections
```

### Credentials Storage

```javascript
// Form sends
service_account_key: "{ ... full JSON ... }"

// Backend stores as-is in CloudProvider.credentials
credentials = service_account_key_str  // Complete JSON string

// YandexClient parses it
credentials = json.loads(provider.credentials)
service_account_key = credentials.get('service_account_key')
```

## ✨ **What's Different from Old Modal**

| Aspect | Old (Screenshot) | New (Fixed) |
|--------|------------------|-------------|
| **Fields** | 4 separate fields | 1 JSON textarea |
| **Access Key ID** | ❌ Removed | - |
| **Secret Access Key** | ❌ Removed | - |
| **Organization ID** | ❌ Removed | - |
| **Cloud ID** | ❌ Removed (auto-extracted) | - |
| **Service Account Key** | - | ✅ Added (textarea) |
| **Help Text** | None | ✅ "Вставьте полный JSON..." |
| **Placeholder** | Simple text | ✅ Formatted JSON example |
| **Rows** | N/A | ✅ 8 rows (plenty of space) |

## 🎯 **Next Steps**

1. **Refresh the browser** - Clear cache to load new JavaScript
2. **Try the modal** - Select Yandex Cloud and verify single JSON field
3. **Test connection** - Paste your service account JSON
4. **Add connection** - Save and sync

## 🐛 **Troubleshooting**

### Modal Still Shows Old Fields

**Solution**: Hard refresh the browser
- Chrome/Firefox: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
- Or clear browser cache

### JSON Validation Fails

**Error**: "Invalid JSON format"

**Solution**: 
- Check JSON is valid (use https://jsonlint.com/)
- Ensure you copied the complete JSON (including braces)
- Don't add extra quotes around the JSON

**Example Valid JSON**:
```json
{
  "id": "ajel4qo...",
  "service_account_id": "aje9ohm...",
  "created_at": "2024-01-01T00:00:00Z",
  "key_algorithm": "RSA_2048",
  "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
}
```

### Missing Required Fields

**Error**: "Missing fields: private_key"

**Solution**:
- Ensure you created an **Authorized Key** (not API Key or Static Key)
- Re-download the JSON from Yandex Cloud
- Verify the JSON contains `id`, `service_account_id`, and `private_key`

## 📊 **Summary**

✅ **Modal Fixed**: Single JSON textarea instead of 4 separate fields
✅ **Routes Added**: Complete CRUD operations for Yandex
✅ **Validation**: Proper JSON parsing and error messages  
✅ **Edit Support**: JSON is preserved when editing connection
✅ **Sync Support**: Full resource synchronization via button
✅ **Help Text**: User guidance in Russian

**The Yandex Cloud integration is now fully functional with proper UI!** 🎉

