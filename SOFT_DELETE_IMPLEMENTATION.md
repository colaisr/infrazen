# Soft Delete Implementation for Provider Connections

**Date:** October 30, 2025  
**Status:** ✅ Implemented and Tested

## Overview

InfraZen implements **soft delete** for cloud provider connections to preserve historical data for FinOps analytics while allowing users to remove connections from their active view.

## Why Soft Delete?

As a **FinOps platform**, historical cost data is critical for:
- 📊 Cost trend analysis over time
- 📈 Budget forecasting
- 🔍 Audit trails for compliance
- 💰 Understanding past spending patterns
- 📉 Identifying cost optimization opportunities

**Hard delete would permanently destroy this valuable financial data.**

## Implementation Details

### Database Schema

Two new fields added to `cloud_providers` table:

```sql
is_deleted BOOLEAN NOT NULL DEFAULT 0 (indexed)
deleted_at DATETIME NULL
```

**Migration:** `b2d7e551d226_add_soft_delete_to_cloud_providers.py`

### Unique Constraint Update

**Old constraint:**
```sql
UNIQUE (user_id, connection_name)
```

**New constraint:**
```sql
UNIQUE (user_id, connection_name, is_deleted)
```

This allows users to **reuse connection names** after deleting the old connection.

**Example:**
- ✅ Active: `(user_id=2, name='yc-private', is_deleted=0)`
- ✅ Deleted: `(user_id=2, name='yc-private', is_deleted=1)`

**Migration:** `4ada00ea0a53_update_unique_constraint_for_soft_delete.py`

## Behavior

### Before Deletion
- Provider visible on `/connections` page ✅
- Provider included in syncs ✅
- Provider included in analytics ✅
- Resources and snapshots accessible ✅

### After Soft Deletion
- Provider **hidden** from `/connections` page ❌
- Provider **excluded** from syncs ❌
- Provider **excluded** from dashboard ❌
- Provider **excluded** from analytics charts ❌
- Historical data **preserved** in database ✅
- Sync snapshots **remain intact** ✅
- Resources **remain in database** ✅
- Cost history **available for reports** ✅

## Code Changes

### 1. Model Updates

**File:** `app/core/models/provider.py`

```python
# Added fields
is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
deleted_at = db.Column(db.DateTime)

# Updated constraint
db.UniqueConstraint('user_id', 'connection_name', 'is_deleted', 
                    name='unique_user_active_connection')
```

### 2. Delete Endpoints (All Providers)

**Files:**
- `app/providers/beget/routes.py`
- `app/providers/selectel/routes.py`
- `app/providers/yandex/routes.py`

**Before:**
```python
db.session.delete(provider)
db.session.commit()
```

**After:**
```python
from datetime import datetime

provider.is_deleted = True
provider.deleted_at = datetime.utcnow()
provider.is_active = False
db.session.commit()
```

### 3. Query Filters (All Locations)

All `CloudProvider.query` calls updated to filter out soft-deleted providers:

```python
# Before
CloudProvider.query.all()

# After
CloudProvider.query.filter_by(is_deleted=False).all()
```

**Updated Files:**
- `app/web/main.py` - Dashboard, connections, resources pages (8 locations)
- `app/api/providers.py` - Provider listing API
- `app/core/services/complete_sync_service.py` - Sync orchestrator

### 4. Cascade Delete Relationships

**Fixed Cascade Issues:**

To prevent foreign key constraint errors during deletion, added proper cascade relationships:

**CloudProvider relationships:**
```python
resources = db.relationship('Resource', cascade='all, delete-orphan')
sync_snapshots = db.relationship('SyncSnapshot', cascade='all, delete-orphan')
provider_sync_references = db.relationship('ProviderSyncReference', cascade='all, delete-orphan')
recommendations = db.relationship('OptimizationRecommendation', cascade='all, delete-orphan')
```

**Resource relationships:**
```python
price_comparison_recommendations = db.relationship('PriceComparisonRecommendation', cascade='all, delete-orphan')
# board_placements backref defined in BoardResource model
```

**Note:** Cascade is configured at ORM level, but actual deletion doesn't happen due to soft delete implementation.

## User Experience

### Creating New Connection
1. User can create a connection named `my-aws-prod`
2. Connection shows in connections list

### Deleting Connection
1. User clicks delete button
2. Confirmation dialog appears
3. Connection is soft-deleted:
   - `is_deleted = True`
   - `deleted_at = 2025-10-30 18:15:00`
   - `is_active = False`
4. Connection **disappears** from UI immediately
5. Historical data **remains** in database

### Re-creating Connection
1. User can create **new connection** with same name `my-aws-prod`
2. Old deleted connection (`is_deleted=1`) doesn't conflict
3. New connection (`is_deleted=0`) is completely independent
4. Both exist in database for historical tracking

## Sync Behavior

### Complete Sync Service

**File:** `app/core/services/complete_sync_service.py`

```python
def get_user_providers(self):
    return CloudProvider.query.filter_by(
        user_id=self.user_id,
        auto_sync=True,
        is_active=True,
        is_deleted=False  # Exclude soft-deleted providers
    ).order_by('created_at').all()
```

Soft-deleted providers are **automatically excluded** from all sync operations.

## Analytics & Reporting

### Historical Data Preservation

Even after soft delete, the following data remains accessible for analytics:

1. **Sync Snapshots** - Complete history of all syncs
2. **Resources** - All resources that were synced
3. **Cost Trends** - Historical cost data
4. **Recommendations** - Past optimization recommendations
5. **Resource States** - Changes over time

### Future Analytics Features

The soft delete design enables:
- 📊 "Show deleted providers" toggle in analytics
- 📈 Total spend including deleted providers
- 🔍 Deleted provider drill-down for cost forensics
- 📉 Comparing costs before/after provider removal

## Testing

### Test Scenarios

✅ **Delete active provider** - Removes from UI, preserves data  
✅ **Reuse connection name** - Creates new independent connection  
✅ **Sync excluded** - Deleted provider not synchronized  
✅ **Dashboard excluded** - Deleted provider not in cost calculations  
✅ **Historical data intact** - Sync snapshots remain queryable  
✅ **Cascade relationships** - No foreign key errors on delete

## Database Migrations

### Migration 1: Add Soft Delete Fields
```bash
Revision: b2d7e551d226
Adds: is_deleted (BOOLEAN), deleted_at (DATETIME)
Index: is_deleted
```

### Migration 2: Update Unique Constraint
```bash
Revision: 4ada00ea0a53
Changes: unique_user_connection → unique_user_active_connection
Adds: is_deleted to unique constraint
```

## Future Enhancements

### Potential Features

1. **Admin Panel**
   - View all deleted providers
   - Permanently delete (hard delete) option
   - Bulk delete old providers (e.g., older than 1 year)

2. **User Interface**
   - "Archived Connections" tab
   - Toggle to show/hide deleted providers in analytics
   - Deleted provider cost breakdown in reports

3. **Compliance**
   - GDPR "Right to be Forgotten" - permanent deletion option
   - Data retention policies
   - Export historical data before permanent deletion

4. **Restore Function** (Optional)
   - Currently NOT implemented by design
   - User creates new connection instead
   - Maintains clean separation between old/new connections

## Related Files

### Models
- `app/core/models/provider.py` - CloudProvider model
- `app/core/models/resource.py` - Resource cascades
- `app/core/models/board_resource.py` - Board placement cascades

### API Endpoints
- `app/providers/beget/routes.py` - Beget soft delete
- `app/providers/selectel/routes.py` - Selectel soft delete
- `app/providers/yandex/routes.py` - Yandex soft delete

### Services
- `app/core/services/complete_sync_service.py` - Sync exclusion
- `app/web/main.py` - UI filtering

### Migrations
- `migrations/versions/b2d7e551d226_add_soft_delete_to_cloud_providers.py`
- `migrations/versions/4ada00ea0a53_update_unique_constraint_for_soft_delete.py`

## Summary

Soft delete implementation provides the **best of both worlds**:
- ✅ Users can remove unwanted connections from their view
- ✅ Historical financial data is preserved for FinOps analysis
- ✅ Connection names can be reused
- ✅ Sync operations only target active connections
- ✅ Database integrity maintained with proper cascades

This aligns perfectly with InfraZen's mission as a comprehensive **FinOps platform** where historical cost data is invaluable for financial optimization and planning.






