# Cloud.ru Volume-to-Server Attachment Research

## Problem

Volume `vm-21sch-hq-gitlab-01-infra-infra` appears as a standalone resource in InfraZen but should be grouped with server `vm-21sch-hq-gitlab-01-infra`. The Cloud.ru console shows "Servers: vm-21sch-hq-gitlab-01-infra" when viewing the volume details.

## Research Summary

### Evolution Endpoints Tested (Feb 2026)

Run: `python3 scripts/test_cloud_ru_volume_attachment.py`

| Endpoint | Full URL | Result | Notes |
|----------|----------|--------|-------|
| **EVS volumes/detail** | `evs.ru-moscow-1.hc.sbercloud.ru/v2/{project_id}/volumes/detail` | 401 | Evolution IAM token: "decrypt token fail" |
| **ECS cloudservers/detail** | `ecs.ru-moscow-1.hc.sbercloud.ru/v1/{project_id}/cloudservers/detail` | 401 | Same auth incompatibility |
| **BFF product-instances** | `console.cloud.ru/u-api/bff-console/v1/projects/{id}/product-instances` | 200 | High-level products (Backup, Redis), no VM/volume attachment |
| **SVP servers** | `console.cloud.ru/u-api/svp/svc/v1/projects/{id}/servers` | 404 | Not Found |
| **SVP instances** | `console.cloud.ru/u-api/svp/svc/v1/projects/{id}/instances` | 404 | Not Found |
| **SVP volumes** | `console.cloud.ru/u-api/svp/svc/v1/projects/{id}/volumes` | 404 | Not Found |
| **SVP volumes/detail** | `console.cloud.ru/u-api/svp/svc/v1/projects/{id}/volumes/detail` | 404 | Not Found |
| **SVP disks** | `console.cloud.ru/u-api/svp/svc/v1/projects/{id}/disks` | 404 | Not Found |
| **SVP disk-types** | `console.cloud.ru/u-api/svp/svc/v1/disk-types` | 200 | Disk types only, no volume list |
| **EIV servers** | `console.cloud.ru/u-api/eiv/v1/projects/{id}/servers` | 404 | Not Found |
| **EIV instances** | `console.cloud.ru/u-api/eiv/v1/projects/{id}/instances` | 404 | Not Found |
| **EIV volumes** | `console.cloud.ru/u-api/eiv/v1/projects/{id}/volumes` | 404 | Not Found |
| **u-api EVS volumes** | `console.cloud.ru/u-api/evs/v1/projects/{id}/volumes` | 404 | Not Found |
| **u-api EVS volumes/detail** | `console.cloud.ru/u-api/evs/v2/{id}/volumes/detail` | 404 | Not Found |

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

### Compute API Disk-to-VM Mapping (Feb 2026)

**VM detail** `GET compute.api.cloud.ru/api/v1/vms/{vm_id}?project_id=xxx` returns `disks[]` with disk id.

1. **CloudRuClient.get_disk_to_vm_mapping()**: Fetches all VMs per project, then VM detail for each; builds `disk_id → {vm_id, vm_name}`.
2. **Plugin grouping**: For volume billing records, if `resource_id` (disk_id) is in the mapping, use `vm_name` as grouping key instead of name heuristics.
3. **Fallback**: When mapping is empty (API failure, no VMs), falls back to name heuristics.

### Heuristic Fallback (unchanged)

- `*-volume*` → strip from `-volume`
- `*-infra-infra` → server `{name}-infra`
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

## Web Research (Feb 2026)

### Cloud.ru Evolution API Registry

From [cloud.ru/docs/console_api/ug/topics/overview__reestr_api](https://cloud.ru/docs/console_api/ug/topics/overview__reestr_api):

- **VMs**: `https://compute.api.cloud.ru` – documented, REST + gRPC
- **VPC**: `https://vpc.api.cloud.ru`
- **Object Storage**: S3E
- **No separate "Disks" or "Block Storage" API** listed for Evolution

### Evolution vs Advanced

| Platform | Base | Volumes/Disks |
|----------|------|---------------|
| **Evolution** (console.cloud.ru) | compute.api.cloud.ru, vpc.api.cloud.ru | Not in public API registry |
| **Advanced** (hc.sbercloud.ru) | evs.ru-moscow-1.hc.sbercloud.ru, ecs.ru-moscow-1.hc.sbercloud.ru | EVS API has `attachments[].server_id` – returns 401 with Evolution tokens |

### Endpoints Tested (Feb 2026 – after web research)

| Endpoint | Result | Notes |
|----------|--------|-------|
| `GET compute.api.cloud.ru/api/v1/disks` | **403 Forbidden** | Endpoint exists; service account lacks permission |
| `GET compute.api.cloud.ru/api/v1/volumes` | 404 | Not Found |
| `GET compute.api.cloud.ru/api/v1/vms` | **200** | Returns VMs; list response has no disks/volumes/attachments |
| `GET compute.api.cloud.ru/api/v1/projects/{id}/disks` | 404 | Not Found |
| `GET compute.api.cloud.ru/api/v1/projects/{id}/volumes` | 404 | Not Found |

**Key finding**: `compute.api.cloud.ru/api/v1/disks` returns 403 (not 404), so the disks API exists but requires additional permissions for the service account.

### Endpoints to Try Next

1. **Compute API – VM detail** (may include attached disks):
   - `GET https://compute.api.cloud.ru/api/v1/vms/{vm_id}` (with `project_id`)

2. **HAR capture**: Open a volume in console.cloud.ru → Disks → click a volume → "Servers" section. Capture HAR and find the request that loads that section.

## Support Request (for Cloud.ru)

**Question to ask Cloud.ru support:**

> We use the Evolution platform (console.cloud.ru) with service account authentication. We need to programmatically determine which server (VM) a block storage volume is attached to. The consumption API does not include parent_id or server_id.
>
> **Findings:**
> - `GET https://compute.api.cloud.ru/api/v1/disks` returns **403 Forbidden** (not 404) – the endpoint exists but our service account lacks permission. What permissions/roles are needed to access it? Does the response include volume-to-server attachment?
> - `GET compute.api.cloud.ru/api/v1/vms` returns 200, but the VM list has no disks/volumes/attachments. Does a VM detail endpoint (e.g. `GET /vms/{id}`) include attached disks?
> - SVP/EIV/EVS under `console.cloud.ru/u-api/` – all return 404
> - Huawei EVS API (`evs.ru-moscow-1.hc.sbercloud.ru`) returns 401 with Evolution IAM tokens
>
> **Question:** Is there an Evolution API endpoint that returns volume-to-server attachment info (e.g. `attachments[].server_id` or `parent_id`)? If so, what is the exact path and required permissions for a service account?

## Recommendations

1. **HAR capture**: When opening a volume in Cloud.ru console (Evolution), capture HAR and find the API call that loads the "Servers" section. That might reveal the Evolution-specific volume detail endpoint.

2. **Advanced platform**: If using Cloud.ru Advanced (hc.sbercloud.ru), ensure service account has EVS read permissions and use the same IAM domain. The EVS API would then return `attachments[].server_id`.

3. **Heuristic maintenance**: If new volume naming patterns appear (e.g. `*-data-data`), add them to `_extract_base_name_for_grouping()`.
