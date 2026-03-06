# Cloud.ru Evolution — Complete API Reference for Resource Discovery

## Overview

Tested: Feb 2026. Project ID: `0ae87bd4-4675-4d08-9103-387a87b3de40`.
Auth: Service Account key → `POST iam.api.cloud.ru/api/v1/auth/token` → Bearer JWT.

**Source**: OpenAPI specs downloaded from cloud.ru docs + live testing.

---

## 1. Compute API — `https://compute.api.cloud.ru`

OpenAPI spec: [openapi-v3.yaml](https://cloud.ru/docs/api/specs/virtual-machines/ug/_downloads/43c42ff22a171c77371e690a08181c3f/openapi-v3.yaml)

### 1.1 VMs

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/vms?project_id=` | ✅ 200 | List VMs (short form) |
| `GET /api/v1/vms/{vm_id}?project_id=` | ✅ 200 | VM detail with **disks[], interfaces[], project, image** |

**VM list item** properties:
`id, name, project_id, description, image_id, tags, flavor{id,name,cpu,ram,gpu,oversubscription,flavor_type{}}, state, locked, created_time, modified_time, interfaces[], availability_zone{id,name}, is_serial_ready, guest_agent_state`

**VM detail** (extra fields vs list):
- `disks[]` — each disk: `{id, name, primary, size, state, serial_id, tags, disk_type{id,name}, limit_bw, limit_rate}`
- `interfaces[]` — each: `{id, name, ip_address, subnet{id,name,cidr}, floating_ip{id,ip_address}, type, state, primary, security_groups[]}`
- `image{}` — `{id, name, display_name, type}`
- `project{}` — `{id, name}`
- `metadata_fields[]` — key/value metadata
- `placement_group` — if set

**Key relationships**:
- `vm.disks[].id` = disk_id (can match billing `resource_id`)
- `vm.interfaces[].subnet.id` → subnet
- `vm.interfaces[].floating_ip.id` → floating IP
- `vm.flavor.id` → flavor (cpu/ram/gpu)
- `vm.image.id` → OS image
- `vm.availability_zone.id` → AZ

### 1.2 Disks

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/disks?project_id=` | 🔒 403 | **Exists but forbidden** — need additional permissions |
| `GET /api/v1/disks/{disk_id}?project_id=` | Not tested | May work if list is 403 |
| `POST /api/v1/disks/{disk_id}/attach` | Not tested | Attach disk to VM |
| `POST /api/v1/disks/{disk_id}/detach` | Not tested | Detach disk from VM |

**Workaround**: Get disks from VM detail `GET /api/v1/vms/{vm_id}` → `disks[]`.

### 1.3 Disk Types

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/disk-types?project_id=` | ✅ 200 | List disk types |

Properties: `id, name, display_name, speed_limits{read_bw,write_bw,read_iops,write_iops}, free_tier, min_size, max_size, availability_zones[]`

### 1.4 Images

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/images?project_id=` | ✅ 200 | 48 images |

Properties: `id, name, display_name, description, project_id, min_cpu, min_ram, min_disk, min_gpu, type, public, image_metadata{os_name,os_version}, availability_zones[]`

### 1.5 Flavors

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/flavors?project_id=` | ✅ 200 | 50 flavors |
| `GET /api/v1/flavor-types` | ✅ 200 | 21 flavor types |

**Flavor** properties: `id, name, description, type, flavor_type{id,name,old_name,display_name,cpu_type,gpu_type,oversubscription}, cpu, ram, gpu, oversubscription, assured_bandwidth, maximum_bandwidth, pps, availability_zones[]`

### 1.6 Interfaces (Network)

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/interfaces?project_id=` | ✅ 200 | All network interfaces |

Properties: `id, name, description, ip_address, subnet{id,name,cidr,vpc{}}, vm{id,name}, security_groups[], floating_ip{id,ip_address}, type, state, primary, project{id,name}, availability_zone{}`

**Key relationships**:
- `interface.vm.id` → VM (reverse: find which VM an interface belongs to)
- `interface.subnet.id` → subnet → VPC
- `interface.floating_ip.id` → public IP

### 1.7 Subnets

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/subnets?project_id=` | ✅ 200 | May return 0 in free tier |

### 1.8 Floating IPs

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/floating-ips?project_id=` | ✅ 200 | Public IPs |

Properties: `id, name, ip_address, state, description, interface{id}, vm{id,name}, server{id,name}, nat_gateway{}, availability_zone{}, tags[]`

**Key relationships**:
- `floating_ip.vm.id` → attached VM
- `floating_ip.interface.id` → attached interface

### 1.9 Security Groups

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/security-groups?project_id=` | ✅ 200 | Firewall rules |

Properties: `id, name, description, project{}, default, has_interfaces, ingress_rules_count, egress_rules_count, availability_zone{}, tags[], state`

### 1.10 Backups

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/backups?project_id=` | ✅ 200 | Backup policies |

Properties: `id, name, description, project_id, state, created_at, updated_at, last_restore_time, retention_policy{}, size, tags[], resource{}`

**Key relationships**:
- `backup.resource` → what is being backed up (VM or disk)

### 1.11 NAT Gateways

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/nat-gateways?project_id=` | ✅ 200 | NAT gateways |

### 1.12 Placement Groups

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/placement-groups?project_id=` | ✅ 200 | Anti-affinity groups |

### 1.13 Availability Zones

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/availability-zones?project_id=` | ✅ 200 | 3 AZs |

Properties: `id, name, display_name, description, enabled, short_name, default`

### 1.14 Tasks

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/tasks?project_id=` | ✅ 200 | Async operation tasks |

Properties: `id, name, status, created_time, modified_time, user_id, user_email, entity_id, entity_type, entity_name`

### 1.15 Reference Data

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/params/vm` | ✅ 200 | VM creation parameters |
| `GET /api/v1/params/disk` | ✅ 200 | Disk parameters |
| `GET /api/v1/params/subnet` | ✅ 200 | Subnet parameters |
| `GET /api/v1/params/flavor` | ✅ 200 | Flavor parameters |
| `GET /api/v1/free-tier` | ✅ 200 | Free tier limits |
| `GET /api/v1/project-entity-usage` | ✅ 201 | Quotas/usage |

### 1.16 Price Calculation

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/v1/projects/{project_id}/price-calculation` | ✅ (from HAR) | VM pricing |

---

## 2. VPC API — `https://vpc.api.cloud.ru`

OpenAPI spec: [openapi.yaml](https://cloud.ru/docs/api/specs/evolution-vpc/ug/_downloads/113b453e0e2aa12a22311dfa29cac9ef/openapi.yaml)

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /v1/vpcs?projectId=` | ✅ 200 | List VPCs |
| `GET /v1/vpcs/{vpcId}` | Not tested | VPC detail |
| `GET /v1/vpcs/{vpcId}/routes/static` | Not tested | Static routes |

**VPC** properties: `id, name, projectId, customerId, createdAt, default, productInstanceId, type(CLIENT/SERVICE), description, updatedAt`

---

## 3. Managed Kubernetes API

| Endpoint | Status | Notes |
|----------|--------|-------|
| `console.cloud.ru/u-api/mk8s/v2/clusters?project_id=` | ✅ 200 | May return empty for this project |
| `api.sks.dzo.sbercloud.org/api/v1/clusters` | ❌ 404 | Wrong base URL for Evolution |

---

## 4. Console BFF API — `https://console.cloud.ru/u-api/`

| Endpoint | Status | Notes |
|----------|--------|-------|
| `bff-console/v1/projects/{id}/product-instances` | ✅ 200 | 30 product instances |
| `svp/svc/v1/disk-types` | ✅ 200 | Same as Compute disk types |

**Product Instance** properties: `id, product{id,name,int_name}, offering_id, service_instance_id, project_id, name, status, created_at, updated_at, is_trial, agreement_id`

---

## 5. Billing API — `https://organization.api.cloud.ru`

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /v1/consumption?project_ids=&start_date=&end_date=` | ✅ 200 | Consumption records |

**Consumption** properties: `dog_id, dmid, sku, servname, resource_id, resource_name, usedate, amount, amount_nds, cost, unit, usefact, platform, meta{iam_project_name,tenant_name}, updated_dt`

---

## Resource Relationship Map

```
PROJECT
├── VPC (vpc.api.cloud.ru → vpcs)
│   ├── Subnet (compute → subnets)
│   │   └── Interface (compute → interfaces)
│   │       ├── VM (compute → vms)
│   │       │   ├── Disk (vm detail → disks[])
│   │       │   ├── Interface → Floating IP
│   │       │   ├── Flavor (cpu/ram/gpu)
│   │       │   ├── Image (OS)
│   │       │   └── Security Groups
│   │       └── Floating IP (compute → floating-ips)
│   └── NAT Gateway (compute → nat-gateways)
├── Backup (compute → backups → resource{})
├── K8s Cluster (mk8s → clusters)
│   └── Node Pool → VMs (same compute VMs)
├── Product Instances (bff → product-instances)
└── Billing (organization → consumption)
```

## ID Linkage

| From | Field | Links to |
|------|-------|----------|
| VM detail | `disks[].id` | Disk ID (= billing `resource_id`) |
| VM detail | `interfaces[].subnet.id` | Subnet |
| VM detail | `interfaces[].floating_ip.id` | Floating IP |
| VM detail | `flavor.id` | Flavor (cpu/ram/gpu) |
| VM detail | `image.id` | Image (OS) |
| VM detail | `availability_zone.id` | AZ |
| VM detail | `project.id` | Project |
| Interface | `vm.id` | VM |
| Interface | `subnet.id` → `subnet.vpc.id` | VPC |
| Floating IP | `vm.id` | VM |
| Floating IP | `interface.id` | Interface |
| Backup | `resource{}` | Backed-up resource |
| Billing | `resource_id` | May match disk_id, VM name, etc. |

## Permissions Issue

`GET /api/v1/disks` returns **403 Forbidden**. This is the only blocked endpoint.
Service account needs additional role/permission for direct disk listing.
**Workaround**: Iterate VMs → VM detail → `disks[]`.

## Action Items

1. **For provider 136** (production): The service account may have a different project scope — need to verify `project_id` and ensure the token grants access to all projects.
2. **Disks API permission**: Ask support for the required role to enable `GET /api/v1/disks`.
3. **K8s clusters**: Need correct project that has K8s resources to test cluster → node pool → VM chain.
4. **Use ID-based grouping**: Replace name heuristics with:
   - VM detail → `disks[].id` for disk-to-VM
   - Interface → `vm.id` for network-to-VM
   - Floating IP → `vm.id` for IP-to-VM
   - Backup → `resource{}` for backup-to-resource
