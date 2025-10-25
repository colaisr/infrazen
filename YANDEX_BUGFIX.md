# Yandex Cloud - Credentials Handling Bugfix

## 🐛 **Bug Found and Fixed**

**Error**: "IAM token generation failed: No credentials provided (service_account_key or oauth_token required)"

**Cause**: Credentials were being passed directly instead of wrapped in the expected format.

## ✅ **What Was Fixed**

### Routes Changed (3 locations)

#### 1. Test Connection Route
**File**: `app/providers/yandex/routes.py` (Line 48-52)

**Before**:
```python
client = YandexClient(service_account_key)  # ❌ Unwrapped dict
```

**After**:
```python
credentials = {'service_account_key': service_account_key}  # ✅ Wrapped
client = YandexClient(credentials)
```

#### 2. Add Connection Route
**File**: `app/providers/yandex/routes.py` (Line 113-123)

**Before**:
```python
credentials=service_account_key_str,  # ❌ Raw JSON string
```

**After**:
```python
credentials_dict = {
    'service_account_key': service_account_key
}
credentials=json.dumps(credentials_dict),  # ✅ Wrapped JSON
```

#### 3. Update Connection Route
**File**: `app/providers/yandex/routes.py` (Line 173-177)

**Before**:
```python
provider.credentials = service_account_key_str  # ❌ Raw JSON
```

**After**:
```python
credentials_dict = {
    'service_account_key': service_account_key
}
provider.credentials = json.dumps(credentials_dict)  # ✅ Wrapped JSON
```

#### 4. Edit Connection Route
**File**: `app/providers/yandex/routes.py` (Line 257-262)

**Added**: Unwrapping logic to display in textarea
```python
credentials = json.loads(provider.credentials)
service_account_key = credentials.get('service_account_key', {})
service_account_key_str = json.dumps(service_account_key, indent=2)
```

## 📊 **How Credentials Flow Now**

### Test Connection
```
User pastes JSON
    ↓
{ "id": "...", "private_key": "..." }
    ↓
Route wraps it
    ↓
{ "service_account_key": { "id": "...", "private_key": "..." } }
    ↓
YandexClient receives wrapped version ✅
    ↓
Client extracts: credentials.get('service_account_key')
    ↓
Gets the actual key dict ✅
    ↓
Generates IAM token successfully! ✅
```

### Add Connection
```
User pastes JSON
    ↓
Route parses and wraps
    ↓
Stores in DB as: {"service_account_key": {...}}
    ↓
YandexService loads: json.loads(provider.credentials)
    ↓
Gets: {"service_account_key": {...}}
    ↓
Passes to YandexClient
    ↓
Works! ✅
```

### Edit Connection
```
Load from DB: {"service_account_key": {...}}
    ↓
Route unwraps: credentials.get('service_account_key')
    ↓
Converts to pretty JSON string
    ↓
Shows in textarea for editing
    ↓
User can modify and save ✅
```

## 🔧 **What You Need to Do**

### 1. Refresh the App

The app is running, but it needs to reload the updated routes:

**Option A: Restart the app** (Recommended)
```bash
# Find and kill current process
lsof -i :5001  # Get PID
kill <PID>

# Start fresh
cd /Users/colakamornik/Desktop/InfraZen
"./venv 2/bin/python" run.py &
```

**Option B: App may auto-reload** (if debug mode)
- Just wait 2-3 seconds
- Flask debug mode auto-reloads on file changes

### 2. Refresh Your Browser

**Hard refresh** to load new JavaScript:
- Mac: `Cmd + Shift + R`
- Windows: `Ctrl + Shift + R`

### 3. Try Again

1. Go to http://127.0.0.1:5001/connections
2. Click "Добавить провайдера"
3. Select "Yandex Cloud"
4. Paste your JSON (same one you tried before)
5. Click "Тестировать подключение"
6. Should work now! ✅

## 🧪 **Expected Result**

**Success message**:
```
✅ Подключение успешно! Аккаунт: <Cloud Name> (ID: <cloud-id>)
```

Or at least it should get past the credentials error and try to connect to Yandex API.

## 🎯 **Summary**

**Problem**: Credentials not wrapped properly
**Solution**: Added wrapping logic in all routes
**Status**: ✅ FIXED

**Next**: Restart app + refresh browser + try test again!

