# Yandex Cloud - Datetime Parsing Fix

## 🐛 **Second Bug Fixed**

**Error**: 
```
IAM token generation failed: Failed to generate IAM token from service account: 
Invalid isoformat string: '2025-10-26T04:41:00.714635763+00:00'
```

**Cause**: Yandex Cloud returns timestamps with **nanosecond precision** (9 digits), but Python's `datetime.fromisoformat()` only supports **microsecond precision** (6 digits).

## 📊 **The Problem**

**Yandex API returns**:
```
2025-10-26T04:41:00.714635763+00:00
                       ^^^^^^^^^ 9 digits (nanoseconds)
```

**Python expects**:
```
2025-10-26T04:41:00.714635+00:00
                       ^^^^^^ 6 digits max (microseconds)
```

## ✅ **The Solution**

Added helper method to truncate nanoseconds to microseconds:

```python
def _truncate_to_microseconds(self, timestamp_str: str) -> str:
    """
    Truncate nanosecond precision to microsecond precision
    
    Yandex Cloud: 2025-10-26T04:41:00.714635763+00:00 (9 digits)
    Python needs:  2025-10-26T04:41:00.714635+00:00 (6 digits)
    """
    import re
    pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)([\+\-]\d{2}:\d{2}|Z)'
    match = re.match(pattern, timestamp_str)
    
    if match:
        date_time = match.group(1)
        fractional = match.group(2)
        timezone = match.group(3)
        
        # Truncate to 6 digits (microseconds)
        fractional_truncated = fractional[:6]
        
        return f"{date_time}.{fractional_truncated}{timezone}"
    
    return timestamp_str
```

**Applied in 2 locations**:
1. ✅ `_get_iam_token_from_service_account()` - Line 163
2. ✅ `_get_iam_token_from_oauth()` - Line 200

## 🔧 **Both Bugs Now Fixed**

### Bug #1: Credentials Not Wrapped ✅
```python
# Fixed in routes.py
credentials = {'service_account_key': service_account_key}
client = YandexClient(credentials)
```

### Bug #2: Datetime Nanoseconds ✅
```python
# Fixed in client.py
expires_at_str = self._truncate_to_microseconds(expires_at_str)
self._iam_token_expires_at = datetime.fromisoformat(expires_at_str)
```

## 🚀 **App Status**

✅ **App restarted** with both fixes
✅ **Running on**: http://127.0.0.1:5001

## 🧪 **Try Connection Test Now**

1. **Refresh browser** (hard refresh: `Cmd+Shift+R`)
2. Go to http://127.0.0.1:5001/connections
3. Click "Добавить провайдера"
4. Select "Yandex Cloud"
5. Paste your JSON (same one as before)
6. Click "Тестировать подключение"
7. **Should work now!** ✅

## 📝 **Expected Success Flow**

```
1. User pastes JSON ✅
2. Route wraps credentials ✅
3. Client parses service account key ✅
4. JWT generated and signed ✅
5. JWT exchanged for IAM token ✅
6. Datetime truncated to microseconds ✅
7. IAM token cached with expiration ✅
8. API call to list clouds ✅
9. Returns: "✅ Connection successful, X clouds found" ✅
```

## 🎯 **Summary**

**Both bugs fixed**:
1. ✅ Credentials properly wrapped/unwrapped
2. ✅ Datetime nanoseconds truncated to microseconds

**App status**: ✅ Restarted with all fixes

**Next step**: Try the test connection again - it should work now!

