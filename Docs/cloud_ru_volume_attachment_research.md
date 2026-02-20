# Cloud.ru Volume-to-Server Attachment Research

## Problem

Volume `vm-21sch-hq-gitlab-01-infra-infra` appears as a standalone resource in InfraZen but should be grouped with server `vm-21sch-hq-gitlab-01-infra`. The Cloud.ru console shows "Servers: vm-21sch-hq-gitlab-01-infra" when viewing the volume details.

## Research Summary

### API Options Investigated

| Endpoint | Base URL | Result | Notes |
|----------|----------|--------|-------|
| **EVS volumes/detail** | `evs.ru-moscow-1.hc.sbercloud.ru` | 401 | Evolution IAM token doesn't work with Advanced (hc.sbercloud.ru) |
| **ECS cloudservers/detail** | `ecs.ru-moscow-1.hc.sbercloud.ru` | 401 | Same auth incompatibility |
| **SVP product-instances** | `console.cloud.ru/u-api/bff-console/v1/projects/{id}/product-instances` | 200 | Returns high-level products (Backup, Redis, etc.), not VM/volume inventory |
| **SVP servers/volumes** | `console.cloud.ru/u-api/svp/svc/v1/...` | 404 | Path not found |
| **u-api EVS/EIV** | `console.cloud.ru/u-api/evs/`, `eiv/` | 404 | Path not found |

### Huawei EVS API (Reference)

The Huawei Cloud EVS API (which Cloud.ru Advanced uses) returns volume attachment info:

```
GET /v2/{project_id}/volumes/detail
```

Response includes `attachments` array per volume:
```json
{
  "attachments": [{
    "server_id": "uuid-of-attached-server",
    "volume_id": "...",
    "device": "/dev/vdb"
  }]
}
```

**Limitation**: Evolution platform (console.cloud.ru) uses different auth than Advanced (hc.sbercloud.ru). Service accounts with Evolution tokens get 401 on Advanced endpoints.

### Consumption API

The billing/consumption API (`organization.api.cloud.ru/v1/consumption`) returns:
- `resource_id`, `resource_name`, `servname`, `sku`, etc.
- **No** `parent_id`, `server_id`, or `attached_to` fields in consumption records

## Implemented Solution

### Heuristic Extension

Since no API provides volume-to-server attachment for Evolution platform, the grouping heuristic was extended:

**New pattern**: Volume names ending with `-infra-infra` attach to server `{name}-infra`
- `vm-21sch-hq-gitlab-01-infra-infra` → groups with `vm-21sch-hq-gitlab-01-infra`

Added to `_extract_base_name_for_grouping()` in `app/providers/plugins/cloud_ru.py`.

### Existing Patterns (unchanged)

- `*-volume*` → strip from `-volume`
- `*-volume-0000`, `*-disk-*`, `*-data-*` etc.

## Test Script

Run to discover/validate volume attachment APIs:

```bash
python3 scripts/test_cloud_ru_volume_attachment.py
```

The script:
1. Tries EVS, ECS, SVP, product-instances endpoints
2. Saves product-instances response to `cloud_ru_product_instances_sample.json`
3. Checks consumption API for attachment metadata

## Recommendations

1. **HAR capture**: When opening a volume in Cloud.ru console (Evolution), capture HAR and find the API call that loads the "Servers" section. That might reveal the Evolution-specific volume detail endpoint.

2. **Advanced platform**: If using Cloud.ru Advanced (hc.sbercloud.ru), ensure service account has EVS read permissions and use the same IAM domain. The EVS API would then return `attachments[].server_id`.

3. **Heuristic maintenance**: If new volume naming patterns appear (e.g. `*-data-data`), add them to `_extract_base_name_for_grouping()`.
