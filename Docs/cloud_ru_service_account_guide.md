# Cloud.ru Service Account Setup Guide for InfraZen

## Overview

This guide explains how to create a service account in Cloud.ru with the correct permissions for InfraZen integration.

## Step-by-Step Setup

### 1. Create Service Account

1. Navigate to: **Пользователи → Сервисные аккаунты** (Users → Service Accounts)
2. Click **Создать аккаунт** (Create Account)
3. Enter:
   - **Name**: `infrazen-integration` (or your preferred name)
   - **Description**: "Service account for InfraZen FinOps platform integration"

### 2. Select Project

⚠️ **Important**: Service account can only access **one project**. Choose the project that contains the resources you want to monitor.

- Select your project from the dropdown (e.g., "PP pupu project")
- **Note**: You cannot change the project after creation

### 3. Assign Roles

For InfraZen to work properly, you need **read-only access** to resources and billing data.

#### **Роли на проект** (Roles on Project)

**Recommended Role**: `viewer` or `reader` (read-only access)

This role should provide:
- ✅ List virtual machines
- ✅ List storage volumes
- ✅ List networks
- ✅ View resource specifications
- ✅ View resource costs/billing

**Alternative Roles** (if `viewer` doesn't exist):
- Look for roles like:
  - `compute.viewer` - For VM access
  - `storage.viewer` - For storage access
  - `network.viewer` - For network access
  - `billing.viewer` - For billing/cost access

#### **Роли внутри платформ и сервисов** (Roles within platforms and services)

**For Evolution Platform**:
- If you see Evolution-specific roles, select:
  - `evolution.viewer` or `evolution.reader` - For general Evolution platform access
  - `compute.viewer` - For compute resources
  - `storage.viewer` - For storage resources

**For Other Services**:
- Select viewer/reader roles for any services you use:
  - Databases (if applicable)
  - Load balancers (if applicable)
  - Other services

#### **Роли на организацию** (Roles on Organization)

**Usually NOT needed** for basic resource discovery, but if you need organization-level access:
- Select `organization.viewer` or similar read-only role
- **Warning**: Administrative roles are not recommended unless you need organization-wide access

### 4. Create Access Key

After creating the service account:

1. Click on the service account name
2. Go to **Учетные данные доступа** → **Ключи доступа** (Access Credentials → Access Keys)
3. Click **Создать ключ** (Create Key)
4. Enter description: "InfraZen integration key"
5. Set expiration (or choose "Бессрочно" / Unlimited)
6. Click **Создать** (Create)
7. **IMPORTANT**: Save both:
   - **Key ID** (логин) - This is your `api_key`
   - **Key Secret** (пароль) - This is your `api_secret`
   - ⚠️ You cannot view the secret again after closing the window!

### 5. Use in InfraZen

In InfraZen connection form, enter:
- **API Key**: Your Key ID
- **API Secret**: Your Key Secret
- **Account ID**: Your project ID (optional, can be auto-detected)

## Minimum Required Permissions

For InfraZen to function, the service account needs:

1. **Resource Discovery**:
   - Read access to VMs/compute instances
   - Read access to storage volumes
   - Read access to networks
   - Read access to other resources you want to monitor

2. **Cost/Billing Access** (if available):
   - Read access to billing data
   - Read access to cost information

3. **Account Information**:
   - Read access to account/project metadata

## Testing

After creating the service account and access key:

1. Test connection in InfraZen
2. If connection fails, check:
   - Key ID and Secret are correct
   - Service account has appropriate roles
   - Project is correctly selected
   - Access key hasn't expired

## Troubleshooting

**Connection fails with "Authentication failed"**:
- Verify Key ID and Secret are correct
- Check that access key hasn't expired
- Ensure service account is active

**Connection succeeds but no resources found**:
- Verify service account has `viewer` or `reader` role on the project
- Check that project contains resources
- Verify roles include access to specific services (compute, storage, etc.)

**Cannot see billing/cost data**:
- May require additional `billing.viewer` role
- Some billing data may only be available via web console
- Cost estimation may be used instead of real billing data

## Security Best Practices

1. ✅ Use project-level roles (not organization-level) when possible
2. ✅ Use read-only roles (`viewer`, `reader`)
3. ✅ Set expiration date on access keys (not unlimited)
4. ✅ Rotate keys periodically (at least once per year)
5. ✅ Use separate service account for InfraZen (not shared with other tools)
6. ✅ Monitor service account usage in Cloud.ru console

