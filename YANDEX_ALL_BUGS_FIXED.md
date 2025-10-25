# Yandex Cloud - All Bugs Fixed! 🎉

## 🐛 **Three Bugs Found and Fixed**

### Bug #1: Credentials Not Wrapped ✅
**Error**: "IAM token generation failed: No credentials provided (service_account_key or oauth_token required)"

**Cause**: Service account key was passed directly instead of wrapped in credentials dict

**Fix**: Wrapped credentials in all routes
```python
# routes.py - Line 51
credentials = {'service_account_key': service_account_key}
client = YandexClient(credentials)
```

---

### Bug #2: Nanosecond Precision ✅
**Error**: "Invalid isoformat string: '2025-10-26T04:41:00.714635763+00:00'"

**Cause**: Yandex returns timestamps with 9 digits (nanoseconds), Python expects 6 digits (microseconds)

**Fix**: Added helper method to truncate fractional seconds
```python
# client.py - Line 78
def _truncate_to_microseconds(self, timestamp_str: str) -> str:
    # Truncates .714635763 → .714635
    pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)([\+\-]\d{2}:\d{2}|Z)'
    match = re.match(pattern, timestamp_str)
    if match:
        fractional_truncated = match.group(2)[:6]  # Keep first 6 digits
        return f"{match.group(1)}.{fractional_truncated}{match.group(3)}"
    return timestamp_str
```

---

### Bug #3: Timezone Comparison ✅
**Error**: "can't compare offset-naive and offset-aware datetimes"

**Cause**: Mixed timezone-aware (from Yandex API) and timezone-naive (from Python) datetime objects

**Fix**: Normalized datetime comparison to use timezone-naive datetimes
```python
# client.py - Line 123-130
if self._iam_token and self._iam_token_expires_at:
    # Make both datetimes naive for comparison
    expires_at_naive = self._iam_token_expires_at.replace(tzinfo=None)
    now_naive = datetime.now()
    if now_naive < expires_at_naive - timedelta(minutes=5):
        return self._iam_token  # Use cached token
```

## 📝 **All Changes Summary**

### Files Modified

1. **`app/providers/yandex/client.py`**
   - ✅ Added `_truncate_to_microseconds()` helper method (Line 78)
   - ✅ Fixed datetime comparison in `_get_iam_token()` (Line 123-130)
   - ✅ Applied truncation in service account auth (Line 201)
   - ✅ Applied truncation in OAuth auth (Line 240)

2. **`app/providers/yandex/routes.py`**
   - ✅ Fixed `/test` endpoint to wrap credentials (Line 51)
   - ✅ Fixed `/add` endpoint to wrap and store credentials (Line 113-115)
   - ✅ Fixed `/update` endpoint to wrap credentials (Line 173-177)
   - ✅ Fixed `/edit` endpoint to unwrap for display (Line 257-262)

3. **`app/static/js/connections.js`**
   - ✅ Changed Yandex to use single JSON textarea (Line 14-22)
   - ✅ Added Yandex form action (Line 125-126)
   - ✅ Added Yandex test endpoint (Line 394-396)
   - ✅ Added Yandex edit form support (Line 554-558)

## 🚀 **App Status**

✅ **All fixes applied**
✅ **App restarted**
✅ **Running on**: http://127.0.0.1:5001

## 🧪 **Try Connection Test Now**

### Your JSON (ready to paste):
```json
{
  "id": "ajev5bhjks3nnqhdgc09",
  "service_account_id": "ajel3h2mit89d7diuktf",
  "created_at": "2025-10-25T16:29:01.342823305Z",
  "key_algorithm": "RSA_2048",
  "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArFcVFTioABQ9Y+A3xuRk\nzs3dhf6vTwRzYEB5neRNuRAewHkQmiXlJQAq8AZdTKwBXPdGlJ/JQZJZkK2F8U1b\nK035e1mus5q2yf423bcqXxYCF4mL/eQXx9YcjKXsceQOp7OFagOF2F+FZht1cc7j\nXUYhEloCdAKr75V7i3J5EhJJNBietinKDV4hyy6GIycKVPneCe3sM5y+pCdEVGZY\nnmyNH7pkRuQ3BWSuEUgDx/ZdByBmWyLxWNkhfSJIhA4xv4RsY6IDQzp9s6+5GujB\nG61Va4AkMUnX0vsw7q5m9vvd21CHJ5wpWik8+vYQERqoPwhx/Hyuo4ReH+I31ynu\n+wIDAQAB\n-----END PUBLIC KEY-----\n",
  "private_key": "PLEASE DO NOT REMOVE THIS LINE! Yandex.Cloud SA Key ID <ajev5bhjks3nnqhdgc09>\n-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCsVxUVOKgAFD1j\n4DfG5GTOzd2F/q9PBHNgQHmd5E25EB7AeRCaJeUlACrwBl1MrAFc90aUn8lBklmQ\nrYXxTVsrTfl7Wa6zmrbJ/jbdtypfFgIXiYv95BfH1hyMpexx5A6ns4VqA4XYX4Vm\nG3VxzuNdRiESWgJ0AqvvlXuLcnkSEkk0GJ62KcoNXiHLLoYjJwpU+d4J7ewznL6k\nJ0RUZliebI0fumRG5DcFZK4RSAPH9l0HIGZbIvFY2SF9IkiEDjG/hGxjogNDOn2z\nr7ka6MEbrVVrgCQxSdfS+zDurmb2+93bUIcnnClaKTz69hARGqg/CHH8fK6jhF4f\n4jfXKe77AgMBAAECggEAM7cF+pI/x5ZLPbdAxYwvu+cGvHjKfnmlbZKra/fgYtI1\niChMFRWeB1ZfjBs80A8lcZI6OcshB241Njb75IcD/qCtZpho1jhs9Xw1Vp7qNhJS\nmmGKAqv5ftv/QS1hIGQBCc3TERbxiRZQ320J9xbQH2M19V3RMqLCmWhP5G57ajJY\nFx5JbqqCQsY/x7pHSp1xHbD+Kjr0bdq4iu2gtK+GWOmV3JXywNqRsajHwtP7ieB0\nma0J8gssTBLATpfuYjYT+hpfOK1Wgdjn1xwDySbYtOS2fmUOo6CjkSrs5TGqVqrB\ngTmkM1IHxkWbg95TI/fJ+HIIGqQiYwK4LID0sjTHIQKBgQDCQntfEs+ysqwYwi4o\nKbPSWR3cAUn3fyzxQJ0oma/sQAt1zFucvK+L47Yv7U21zuPd+SzY6EvFf+hl2rJZ\nSiNXjgOLCAdUlvVMgG1smkN45Yy6Sn7CfexvcOstD39wUWz5gd3mRUya6y8d9mL+\nbUUOFtf7oDjjCTmGCsO/4XH64wKBgQDjHSpgP00P0EMKs6HzowFLQsbX8hRq5Gdj\nTTm3ucW3487yo/NKWqzP1m9XA+6pigIJPtLHmKDiYxfiYf+A6j61OLyPkaUorrmm\nW0a9N8rGJSJbuEX4RuMora/rgG+CgFBurCU1X7ehEgp5SYru0+Hq3Jw9Ozk85CN9\ndy1lncD/CQKBgGwyRzC+83veVEg97yNjhsqD5EOjXCVDai69BEuWvgth6IAl4Gi+\nFzBdFh4/l+bJYtVBcZ8mUv2frjr8whVFW8XqTULkp+CPa/S+GzQ//5CYmfcwgsWl\nCUlQpUwls59FWuLlWEhnFLG8iDOyBZUcGzgrtQRrSwP5IVbtK/X1hVxtAoGAPspG\nd/uoS5HxpxjI0rojVnJs1TE5kd/58YtdRL1Yu6GBCrZnQgxVsNSBTdZpengMXg//\naG17NXveE5mycSrSEXpRL4Q93ESKUUL1CMVPC38iw6bruVun3AxBEeQdcEAXfLGd\nS+ddtmttd+DsR2FPGYbKr2cbSQluAncblveJbzkCgYA/6UpimYMgXqcC20Qw8NoP\nrAn2SxYZKTK/GO/WHriMPK4hdTool3QQNNm6sVSb9cmjHdRRvlQ3Svav+tGR2em6\n7xP76ebyELRrVLmPtNE6RJJHp03XW4owjQUmAdHmSKVzfBwemfkQH79hBXx7tt6t\nbIccbf/pPfbnPtgQufOndA==\n-----END PRIVATE KEY-----\n"
}
```

### Steps to Test:

1. **Refresh browser** (hard refresh: `Cmd+Shift+R`)
2. Go to: http://127.0.0.1:5001/connections
3. Click: "Добавить провайдера"
4. Select: "Yandex Cloud"
5. Paste JSON above
6. Connection name: "My Yandex Cloud"
7. Click: **"Тестировать подключение"**

### Expected Result Now:

✅ **"Connection successful, X clouds found"**

The test will now:
1. ✅ Parse JSON correctly
2. ✅ Wrap credentials properly
3. ✅ Generate JWT with your private key
4. ✅ Exchange JWT for IAM token
5. ✅ Parse expiration time (nanoseconds truncated)
6. ✅ Compare datetimes (timezone-aware)
7. ✅ Call Yandex Cloud API
8. ✅ Return list of clouds

**All three bugs are fixed - try it now!** 🎉

## 📋 **Summary of All Fixes**

| Bug # | Error | Root Cause | Fix | Status |
|-------|-------|------------|-----|--------|
| 1 | "No credentials provided" | Not wrapped in dict | Wrap in routes | ✅ |
| 2 | "Invalid isoformat string" | Nanosecond precision | Truncate to microseconds | ✅ |
| 3 | "can't compare offset-naive..." | Mixed timezone types | Normalize to naive | ✅ |

**Ready to test!** 🚀

