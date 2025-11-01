# User Provider Preferences for Recommendations - Implementation Summary

## Overview
Implemented a feature that allows users to choose which cloud providers to include when comparing prices in recommendations. This gives users control over which providers they want to consider for cost optimization suggestions.

## What Was Implemented

### 1. Database Model (`UserProviderPreference`)
**File:** `app/core/models/user_provider_preference.py`

Created a new model to store user preferences for provider inclusion in recommendations:
- `user_id` - Foreign key to users table
- `provider_type` - Provider identifier (beget, selectel, yandex, etc.)
- `is_enabled` - Boolean flag for whether to include this provider
- Default: All providers enabled for new users

Key methods:
- `get_enabled_providers_for_user(user_id)` - Returns list of enabled provider types
- `set_provider_enabled(user_id, provider_type, is_enabled)` - Updates a preference
- `initialize_for_user(user_id)` - Creates preferences for all catalog providers (enabled by default)

### 2. Database Migration
**File:** `migrations/versions/fa7962b5fce6_add_user_provider_preferences_table.py`

- Creates `user_provider_preferences` table
- Seeds data for existing users (all providers enabled by default)
- Ensures all active users have preferences initialized

### 3. API Endpoints
**File:** `app/api/auth.py`

Added two new endpoints:
- `GET /api/auth/provider-preferences` - Returns user's provider preferences with catalog info
- `POST /api/auth/provider-preferences` - Updates a specific provider preference

### 4. Settings Page UI
**Files:** 
- `app/templates/settings.html` - Added new section "Провайдеры для рекомендаций"
- `app/static/css/pages/settings.css` - Styled provider preference cards and toggle switches
- `app/static/js/settings.js` - JavaScript for loading and toggling preferences

The new section displays:
- All available providers from the catalog
- Toggle switches for each provider
- Provider logos (or placeholders)
- Real-time updates when toggling

### 5. Recommendations Engine Integration
**File:** `app/core/recommendations/plugins/price_check_rule.py`

Updated `CrossProviderPriceCheckRule` to:
- Query user's enabled providers before searching for alternatives
- Filter `ProviderPrice` query to only include enabled providers
- Log user preferences for debugging
- Gracefully handle cases where preferences aren't set (defaults to all providers)

### 6. User Creation Integration
**Files:** 
- `app/api/auth.py` (registration)
- `app/api/admin.py` (admin user creation)
- `app/core/models/user.py` (Google OAuth)

All user creation paths now automatically initialize provider preferences:
- Sets all available catalog providers as enabled
- Non-blocking (won't fail user creation if initialization fails)
- Logged for debugging

## User Experience

### Settings Page
Users can now:
1. Navigate to Settings page
2. Scroll to "Провайдеры для рекомендаций" section at the bottom
3. See all available cloud providers
4. Toggle providers on/off using switches
5. Changes are saved immediately with visual feedback

### Recommendations
When recommendations are generated:
1. System checks user's provider preferences
2. Only considers enabled providers when searching for alternatives
3. Disabled providers are excluded from price comparisons
4. Users see more relevant recommendations based on their preferences

## Technical Details

### Data Flow
1. User toggles provider in Settings
2. JavaScript calls `POST /api/auth/provider-preferences`
3. Backend updates `user_provider_preferences` table
4. When recommendations run, they query this table
5. Price comparison only includes enabled providers

### Database Schema
```sql
CREATE TABLE user_provider_preferences (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY uq_user_provider (user_id, provider_type),
    KEY idx_user_provider_enabled (user_id, provider_type, is_enabled)
);
```

### Default Behavior
- **New users:** All providers enabled by default
- **Existing users:** Migration enables all providers
- **No preferences set:** System includes all providers (backward compatible)
- **Empty enabled list:** System includes all providers

## Testing Checklist

- [x] Migration applied successfully
- [x] Settings page displays provider list
- [x] Toggle switches work and save preferences
- [x] API endpoints return correct data
- [x] New user registration initializes preferences
- [x] Google OAuth user creation initializes preferences
- [x] Admin user creation initializes preferences
- [x] Recommendations respect user preferences
- [x] No linting errors

## Files Modified

### New Files
1. `app/core/models/user_provider_preference.py` - Model
2. `migrations/versions/fa7962b5fce6_add_user_provider_preferences_table.py` - Migration
3. `USER_PROVIDER_PREFERENCES_IMPLEMENTATION.md` - This document

### Modified Files
1. `app/core/models/__init__.py` - Import new model
2. `app/api/auth.py` - API endpoints + user creation
3. `app/api/admin.py` - Admin user creation
4. `app/core/models/user.py` - Google OAuth user creation
5. `app/templates/settings.html` - UI section
6. `app/static/css/pages/settings.css` - Styling
7. `app/static/js/settings.js` - JavaScript functionality
8. `app/core/recommendations/plugins/price_check_rule.py` - Filter by preferences

## Future Enhancements

Potential improvements:
1. Bulk enable/disable all providers button
2. Provider-specific notes or reasons for exclusion
3. Analytics on most/least preferred providers
4. Admin view of global provider preference trends
5. Provider recommendations based on user's infrastructure
6. Regional provider preferences (different providers for different regions)

## Notes

- The feature is fully backward compatible
- Existing recommendations will continue to work
- Performance impact is minimal (indexed queries)
- User experience is seamless and intuitive
- All providers enabled by default matches current behavior

