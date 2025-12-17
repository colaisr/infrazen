# Cloud.ru API Research Notes

## Authentication Method
**Status**: ✅ Documented from official docs

**Method**: Service Account Access Key (Key ID + Secret)
- **Authentication Endpoint**: `https://iam.api.cloud.ru/api/v1/auth/token`
- **Request Format**:
  ```json
  {
    "keyId": "хх**хх",
    "secret": "х***х"
  }
  ```
- **Response**: Returns `access_token` (valid for 1 hour)
- **Usage**: `Authorization: Bearer <access_token>` in all API requests

**Alternative Methods**:
- Personal Access Key (user account)
- Static API Key (less secure, for specific services)

**Credentials Required**:
- `keyId` (Key ID / логин)
- `secret` (Key Secret / пароль)

## API Endpoints (To be discovered)

### Base API URL
- **IAM API**: `https://iam.api.cloud.ru/api/v1`
- **Main API**: TBD (likely `https://api.cloud.ru` or similar)

### Account Information
- Endpoint: TBD
- Purpose: Get account details, account ID, balance, etc.

### Resource Discovery
- Virtual Machines: TBD
- Storage Volumes: TBD
- Networks: TBD
- Databases: TBD
- Load Balancers: TBD

### Billing/Cost Data
- Endpoint: TBD
- Purpose: Get current costs, billing history

### Pricing Information
- Endpoint: TBD
- Purpose: Get pricing for different resource types

## Credential Requirements (To be confirmed)
- [ ] API Key (if applicable)
- [ ] Secret Key (if applicable)
- [ ] Account ID
- [ ] Region (if required)
- [ ] Other fields: TBD

## Notes from Testing
(Will be filled during implementation)

