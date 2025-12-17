# Cloud.ru Pricing Endpoint Discovery Results

## Summary

Attempted to discover pricing endpoints programmatically by exploring the `/u-api/` API structure.

## Discovery Method

1. **Script**: `scripts/discover_cloud_ru_pricing_endpoints.py`
2. **Approach**: 
   - Use existing Cloud.ru connection from database
   - Authenticate and get product list
   - Try common pricing endpoint patterns for each product
   - Document discovered endpoints

## Results

### ✅ Known Endpoints (From HAR Files)

These endpoints were already discovered from HAR file analysis:

1. **VM/Compute Pricing**
   - `POST /u-api/svp/svc/v1/projects/{project_id}/price-calculation`
   - Status: ✅ Verified working

2. **Kubernetes Pricing**
   - `POST /u-api/mk8s/v2/billing/calculate-price-ext`
   - Status: ✅ Verified working

3. **Load Balancer Pricing**
   - `GET /u-api/svp/v2/nlb/calculate-price`
   - Status: ✅ Verified working

4. **Database Pricing**
   - `POST /u-api/paas-bff/api/v1/price-calculator/sku-list`
   - Status: ✅ Verified working

### ❌ Limitations Discovered

1. **Product Discovery Endpoint**: 
   - `GET /u-api/bff-console/v1/project/{project_id}/aggregated-available-products`
   - Status: ❌ **403 Forbidden (RBAC: access denied)**
   - **Issue**: Service account doesn't have permission to access this endpoint
   - **Workaround**: Use known products from HAR file analysis

2. **Pattern-Based Discovery**:
   - Tried common patterns like:
     - `/u-api/{product}/v*/billing/calculate-price`
     - `/u-api/{product}/v*/price-calculation`
     - `/u-api/{product}-bff/v*/price-calculator`
   - **Result**: No endpoints found with these patterns
   - **Reason**: Cloud.ru uses non-standard endpoint paths:
     - VMs use: `/u-api/svp/svc/v1/...` (not `/u-api/eiv/...`)
     - Databases use: `/u-api/paas-bff/api/v1/...` (not `/u-api/dbaas/...`)
     - Load Balancers use: `/u-api/svp/v2/nlb/...` (not `/u-api/nlb/...`)

### 📋 Products Tested

Tested pricing endpoint discovery for these products (from HAR analysis):
- S3E (Evolution Object Storage)
- ARTIFACT_REGISTRY (Evolution Artifact Registry)
- CDN
- MONAAS (Cloud Monitoring)
- LOGGING_AS_A_SERVICE (Logging)
- AGENT_BACKUP (Evolution Agent Backup)
- SERVERLESS_CONTAINER (Evolution Container Apps)
- EIV (Evolution Compute)
- MK8S (Evolution Managed Kubernetes)
- NLB (Evolution Load Balancer)
- DBAAS_POSTGRESQL (Evolution Managed PostgreSQL)
- PAAS_REDIS (Evolution Managed Redis)
- PAAS_KAFKA (Evolution Managed Kafka)

**Result**: No additional pricing endpoints discovered via pattern matching.

## Conclusion

### What Works

✅ **HAR File Analysis**: Most effective method for discovering endpoints
- Captures real API calls from browser
- Shows exact endpoint paths, parameters, and responses
- No permission issues

✅ **Known Endpoints**: 4 pricing endpoints verified and working:
- VMs, Kubernetes, Load Balancers, Databases

### What Doesn't Work

❌ **Programmatic Discovery**: Limited by:
- RBAC permissions (can't access product discovery endpoint)
- Non-standard endpoint naming (can't predict paths from product names)
- Need specific parameters/body for each endpoint

### Recommendation

**Continue using HAR file analysis** for discovering new pricing endpoints:
1. User captures HAR file when creating/configuring a service
2. Analyze HAR file to find pricing endpoints
3. Document endpoint structure
4. Implement in pricing client

**For services we haven't discovered yet** (S3, Container Registry, Backup, Monitoring, Logging, CDN):
- Request HAR files from user when they access these services
- Analyze HAR files to find pricing endpoints
- Implement pricing support

## Next Steps

1. ✅ Document known pricing endpoints (DONE)
2. ⏳ Implement pricing client for 4 known services (VMs, K8s, LB, DB)
3. ⏳ Request HAR files for remaining services (S3, Registry, Backup, Monitoring, Logging, CDN)
4. ⏳ Analyze new HAR files when available
5. ⏳ Implement pricing for additional services

