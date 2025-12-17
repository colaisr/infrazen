# Cloud.ru Instruction Page - Screenshots Required

This document lists the screenshots needed for the Cloud.ru instruction page (`app/templates/instructions/cloud_ru.html`).

## Screenshot Location

All screenshots should be placed in: **`app/static/instructions/`**

## Required Screenshots

### 1. Service Accounts List
**Filename**: `cloud_ru_step1_service_accounts.png`  
**Description**: Cloud.ru console showing the "Пользователи" → "Сервисные аккаунты" (Users → Service Accounts) section  
**What to capture**: 
- Left sidebar menu with "Пользователи" (Users) section expanded
- "Сервисные аккаунты" (Service Accounts) option visible
- List of existing service accounts (if any)
- "Создать аккаунт" (Create Account) button visible

---

### 2. Create Service Account Form
**Filename**: `cloud_ru_step2_create_account.png`  
**Description**: Form for creating a new service account  
**What to capture**:
- Service account creation dialog/form
- Name field (e.g., "infrazen-integration")
- Description field
- "Создать" (Create) button

---

### 3. Select Project
**Filename**: `cloud_ru_step3_select_project.png`  
**Description**: Service account page showing project selection  
**What to capture**:
- Service account detail page
- "Роли на проект" (Roles on Project) section
- Project dropdown/selector
- Selected project visible (e.g., "PP pupu project" or similar)

---

### 4. Assign Roles
**Filename**: `cloud_ru_step4_assign_roles.png`  
**Description**: Role assignment interface for the service account  
**What to capture**:
- "Роли на проект" (Roles on Project) section
- Role selector/dropdown showing available roles
- `viewer` or `reader` role selected or visible in the list
- "Роли внутри платформ и сервисов" (Roles within platforms and services) section visible (optional)

---

### 5. Create Access Key Dialog
**Filename**: `cloud_ru_step5_create_key.png`  
**Description**: Dialog for creating a new access key  
**What to capture**:
- "Учетные данные доступа" → "Ключи доступа" (Access Credentials → Access Keys) section
- "Создать ключ" (Create Key) button or dialog
- Key creation form with:
  - Description field (e.g., "InfraZen Integration")
  - Expiration date selector (or "Бессрочно" / Unlimited option)
  - "Создать" (Create) button

---

### 6. Key Credentials Display
**Filename**: `cloud_ru_step6_key_credentials.png`  
**Description**: Window showing the created Key ID and Key Secret  
**What to capture**:
- Success dialog/modal after key creation
- **Key ID** (логин) visible (can be partially masked)
- **Key Secret** (пароль) visible (can be partially masked)
- Warning message about saving the secret (if present)
- "Скопировать" (Copy) buttons or similar

**⚠️ Important**: Make sure the actual secret values are either:
- Fully visible (for documentation purposes)
- Or clearly marked as "example" values
- Or partially masked but with clear indication of what they represent

---

### 7. InfraZen Connection Form
**Filename**: `cloud_ru_step7_infrazen_form.png`  
**Description**: InfraZen connection form with Cloud.ru provider selected  
**What to capture**:
- InfraZen connections page
- "Add Connection" modal/form
- Provider dropdown showing "Cloud.ru" selected
- Form fields visible:
  - "Название подключения" (Connection Name)
  - "API Key" field (with Key ID filled in, can be masked)
  - "API Secret" field (with Key Secret filled in, can be masked)
  - "Тест подключения" (Test Connection) button
  - "Сохранить" (Save) button

---

## Screenshot Guidelines

1. **Resolution**: Use high-resolution screenshots (at least 1920px width recommended)
2. **Format**: PNG format preferred (better for text clarity)
3. **Language**: Screenshots should match the language of the Cloud.ru console (Russian is expected)
4. **Privacy**: 
   - Mask or blur any sensitive information (real Key IDs, Secrets, account numbers)
   - Use example/demo values where possible
   - Or clearly mark screenshots as "example" if using real-looking data
5. **Clarity**: 
   - Ensure text is readable
   - Highlight important UI elements if needed (arrows, boxes, etc.)
   - Crop to focus on relevant sections
6. **Consistency**: 
   - Use similar styling/formatting as other provider screenshots (Beget, Selectel, Yandex)
   - Maintain consistent naming convention: `cloud_ru_step{N}_{description}.png`

---

## Alternative: Using Placeholder Images

If screenshots are not immediately available, you can:
1. Create placeholder images with text descriptions
2. Use annotated screenshots from Cloud.ru documentation (with permission)
3. Create mockups showing the expected UI flow

---

## Testing the Instruction Page

After adding screenshots:

1. Navigate to: `http://127.0.0.1:5001/instructions/cloud-ru`
2. Verify all images load correctly
3. Check that images are properly sized and responsive
4. Ensure image captions are accurate
5. Test the "Закрыть" (Close) button functionality

---

## Current Status

- ✅ Instruction page template created: `app/templates/instructions/cloud_ru.html`
- ✅ Route added to `app/web/main.py`
- ⏳ Screenshots needed: 7 images
- 📁 Screenshot directory: `app/static/instructions/`

---

## Next Steps

1. Take screenshots following the Cloud.ru console workflow
2. Save screenshots with exact filenames listed above
3. Place all screenshots in `app/static/instructions/`
4. Test the instruction page to ensure all images load
5. Update this document when screenshots are added

