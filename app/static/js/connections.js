/**
 * InfraZen - Connections Page JavaScript
 * Handles provider connection management
 */

// ============================================================================
// Provider Configurations
// ============================================================================

const providers = {
    yandex: {
        name: 'Yandex Cloud',
        description: 'Yandex Cloud — российская облачная платформа, предоставляющая услуги виртуальных машин, баз данных, хранилищ и других облачных сервисов.',
        fields: [
            { name: 'access_key', label: 'Access Key ID *', type: 'text', placeholder: 'AQVN...', required: true },
            { name: 'secret_key', label: 'Secret Access Key *', type: 'password', placeholder: '••••••••', required: true },
            { name: 'organization_id', label: 'Organization ID *', type: 'text', placeholder: 'org-1234567890', required: true },
            { name: 'cloud_id', label: 'Cloud ID *', type: 'text', placeholder: 'b1g1234567890', required: true }
        ]
    },
    selectel: {
        name: 'Selectel',
        description: 'Selectel — российский провайдер облачных услуг, специализирующийся на виртуальных серверах, облачными вычислениями и хостинге.',
        fields: [
            { name: 'api_key', label: 'API Key *', type: 'text', placeholder: 'geKYksHLzAeQQLakNjyWnmTLJ_478587', required: true },
            { name: 'service_username', label: 'Service Username *', type: 'text', placeholder: 'InfraZen', required: true },
            { name: 'service_password', label: 'Service Password *', type: 'password', placeholder: '••••••••', required: true }
        ]
    },
    beget: {
        name: 'Beget',
        description: 'Beget — российский хостинг-провайдер, предоставляющий услуги веб-хостинга, регистрации доменов и виртуальных серверов.',
        fields: [
            { name: 'username', label: 'Имя пользователя *', type: 'text', placeholder: 'your_beget_username', required: true },
            { name: 'password', label: 'Пароль *', type: 'password', placeholder: '••••••••', required: true }
        ]
    },
    aws: {
        name: 'Amazon Web Services',
        description: 'Amazon Web Services — ведущая облачная платформа, предоставляющая широкий спектр облачных сервисов и решений.',
        fields: [
            { name: 'access_key_id', label: 'Access Key ID *', type: 'text', placeholder: 'AKIA...', required: true },
            { name: 'secret_access_key', label: 'Secret Access Key *', type: 'password', placeholder: '••••••••', required: true },
            { name: 'region', label: 'Region *', type: 'text', placeholder: 'us-east-1', required: true }
        ]
    },
    azure: {
        name: 'Microsoft Azure',
        description: 'Microsoft Azure — облачная платформа Microsoft, предоставляющая услуги для разработки, тестирования, развертывания и управления приложениями.',
        fields: [
            { name: 'client_id', label: 'Client ID *', type: 'text', placeholder: '12345678-1234-1234-1234-123456789012', required: true },
            { name: 'client_secret', label: 'Client Secret *', type: 'password', placeholder: '••••••••', required: true },
            { name: 'tenant_id', label: 'Tenant ID *', type: 'text', placeholder: '12345678-1234-1234-1234-123456789012', required: true },
            { name: 'subscription_id', label: 'Subscription ID *', type: 'text', placeholder: '12345678-1234-1234-1234-123456789012', required: true }
        ]
    },
    gcp: {
        name: 'Google Cloud Platform',
        description: 'Google Cloud Platform — облачная платформа Google, предоставляющая услуги вычислений, хранения данных и машинного обучения.',
        fields: [
            { name: 'service_account_key', label: 'Service Account Key *', type: 'textarea', placeholder: 'JSON ключ сервисного аккаунта', required: true },
            { name: 'project_id', label: 'Project ID *', type: 'text', placeholder: 'my-gcp-project', required: true }
        ]
    },
    'vk-cloud': {
        name: 'VK Cloud',
        description: 'VK Cloud — российская облачная платформа, предоставляющая услуги виртуальных машин, баз данных и других облачных сервисов.',
        fields: [
            { name: 'access_key', label: 'Access Key *', type: 'text', placeholder: 'vk_access_key', required: true },
            { name: 'secret_key', label: 'Secret Key *', type: 'password', placeholder: '••••••••', required: true },
            { name: 'project_id', label: 'Project ID *', type: 'text', placeholder: 'vk_project_id', required: true }
        ]
    }
};

// ============================================================================
// Modal Management
// ============================================================================

function showProviderModal(selectedProvider = null) {
    document.getElementById('providerModal').style.display = 'block';
    
    // Reset modal to add mode
    resetModalToAddMode();
    
    // If a provider is specified, pre-select it
    if (selectedProvider) {
        const providerSelect = document.getElementById('provider_select');
        providerSelect.value = selectedProvider;
        changeProvider();
    }
}

function closeProviderModal() {
    document.getElementById('providerModal').style.display = 'none';
    document.getElementById('connectionTest').style.display = 'none';
    document.getElementById('testBtn').style.display = 'none';
    document.getElementById('connectBtn').style.display = 'none';
    document.getElementById('provider_select').value = '';
    document.getElementById('providerFields').innerHTML = '';
}

function changeProvider() {
    const selectedProvider = document.getElementById('provider_select').value;
    const providerFields = document.getElementById('providerFields');
    const testBtn = document.getElementById('testBtn');
    const connectBtn = document.getElementById('connectBtn');
    const selectedProviderInput = document.getElementById('selected_provider');
    const form = document.getElementById('providerForm');
    
    if (selectedProvider && providers[selectedProvider]) {
        const provider = providers[selectedProvider];
        
        selectedProviderInput.value = selectedProvider;
        
        // Set form action based on provider
        if (selectedProvider === 'selectel') {
            form.action = '/api/providers/selectel/add';
        } else if (selectedProvider === 'beget') {
            form.action = '/api/providers/beget/add';
        } else {
            form.action = '/api/providers/beget/add';
        }
        
        // Generate dynamic fields
        providerFields.innerHTML = '';
        provider.fields.forEach(field => {
            const fieldHtml = createFieldHtml(field);
            providerFields.innerHTML += fieldHtml;
        });
        
        testBtn.style.display = 'inline-block';
        connectBtn.style.display = 'inline-block';
        
        const editIdField = document.getElementById('edit_connection_id');
        if (editIdField && editIdField.value) {
            connectBtn.textContent = 'Сохранить изменения';
        } else {
            connectBtn.textContent = `Подключить ${provider.name}`;
        }
    } else {
        providerFields.innerHTML = '';
        testBtn.style.display = 'none';
        connectBtn.style.display = 'none';
    }
}

function createFieldHtml(field) {
    const required = field.required ? 'required' : '';
    const placeholder = field.placeholder || '';
    const defaultValue = field.default ? `value="${field.default}"` : '';
    
    if (field.type === 'textarea') {
        return `
            <div class="form-group">
                <label class="form-label" for="${field.name}">${field.label}</label>
                <textarea class="form-control form-textarea" id="${field.name}" name="${field.name}" 
                          placeholder="${placeholder}" ${required}>${field.default || ''}</textarea>
            </div>
        `;
    } else if (field.type === 'password') {
        return `
            <div class="form-group">
                <label class="form-label" for="${field.name}">${field.label}</label>
                <div class="password-input-wrapper">
                    <input type="password" class="form-control" id="${field.name}" name="${field.name}" 
                           placeholder="${placeholder}" ${defaultValue} ${required}>
                    <button type="button" class="password-toggle" onclick="togglePasswordVisibility('${field.name}')">
                        <i class="fa-solid fa-eye" id="eye-${field.name}"></i>
                    </button>
                </div>
            </div>
        `;
    } else {
        return `
            <div class="form-group">
                <label class="form-label" for="${field.name}">${field.label}</label>
                <input type="${field.type}" class="form-control" id="${field.name}" name="${field.name}" 
                       placeholder="${placeholder}" ${defaultValue} ${required}>
            </div>
        `;
    }
}

// ============================================================================
// Connection Management
// ============================================================================

function syncConnection(connectionId, providerType) {
    const numericId = connectionId.includes('-') ? connectionId.split('-')[1] : connectionId;
    const button = event.target.closest('button');
    
    syncProvider(numericId, providerType, button);
}

function editConnection(connectionId) {
    const parts = connectionId.includes('-') ? connectionId.split('-') : [connectionId];
    const providerType = parts.length === 2 ? parts[0] : (document.querySelector(`#provider-${connectionId}`)?.dataset?.providerType || 'beget');
    const numericId = parts.length === 2 ? parts[1] : parts[0];
    
    const button = event?.target?.closest('button');
    const originalText = button ? button.innerHTML : '';
    if (button) {
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Загрузка...</span>';
        button.disabled = true;
    }
    
    const editUrl = `/api/providers/${providerType}/${numericId}/edit`;
    fetch(editUrl)
        .then(async response => {
            const ct = response.headers.get('content-type') || '';
            if (!ct.includes('application/json')) {
                const text = await response.text();
                throw new Error(`Unexpected response (${response.status}): ${text.substring(0, 200)}`);
            }
            const data = await response.json();
            if (data && data.success) {
                showProviderModalForEdit(data.data, providerType);
            } else {
                const msg = (data && (data.error || data.message)) ? (data.error || data.message) : 'Неизвестная ошибка';
                throw new Error(msg);
            }
        })
        .catch(error => {
            showFlashMessage('❌ Ошибка загрузки данных: ' + (error && error.message ? error.message : ''), 'error');
            console.error('Edit error:', error);
        })
        .finally(() => {
            if (button) {
                button.innerHTML = originalText;
                button.disabled = false;
            }
        });
}

function deleteConnection(connectionId, providerType) {
    if (confirm('Вы уверены, что хотите удалить это подключение?\n\nЭто действие нельзя отменить.')) {
        const numericId = connectionId.includes('-') ? connectionId.split('-')[1] : connectionId;
        const button = event.target.closest('button');
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        button.disabled = true;
        
        fetch(`/api/providers/${providerType}/${numericId}/delete`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showFlashMessage('✅ Подключение удалено успешно!', 'success');
                const card = button.closest('.provider-card');
                if (card) {
                    card.style.opacity = '0.5';
                    setTimeout(() => {
                        card.remove();
                    }, 500);
                } else {
                    setTimeout(() => {
                        location.reload();
                    }, 1000);
                }
            } else {
                showFlashMessage('❌ Ошибка удаления: ' + (data.error || data.message), 'error');
            }
        })
        .catch(error => {
            console.error('Delete error details:', error);
            showFlashMessage('❌ Ошибка удаления: ' + error.message, 'error');
        })
        .finally(() => {
            button.innerHTML = originalText;
            button.disabled = false;
        });
    }
}

// ============================================================================
// Recommendations Summary
// ============================================================================

function showRecoSummary() {
    const modal = document.getElementById('recoSummaryModal');
    const body = document.getElementById('recoSummaryBody');
    modal.style.display = 'block';
    body.innerHTML = '<div><i class="fa-solid fa-spinner fa-spin"></i> Загрузка сводки...</div>';
    fetch('/api/recommendations/summary')
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                body.innerHTML = `<div style="color: var(--error-red);">Ошибка: ${data.error}</div>`;
                return;
            }
            const s = data.recommendations_summary || {};
            const timings = s.rule_timings || {};
            const rows = [
                ['Ресурсов обработано', s.resources_processed],
                ['Правил (ресурсных) выполнено', s.resource_rules_run],
                ['Правил (глобальных) выполнено', s.global_rules_run],
                ['Создано рекомендаций', s.recommendations_created],
                ['Обновлено рекомендаций', s.recommendations_updated],
                ['Подавлено (отклонены)', s.suppressed_dismissed],
                ['Подавлено (внедрены)', s.suppressed_implemented],
                ['Подавлено (отложены)', s.suppressed_snoozed],
                ['Пропущено (правило отключено)', s.skipped_rules_disabled],
            ];
            let html = '';
            html += '<div class="provider-info-card">';
            html += `<div class="detail-item"><span class="detail-label">Статус синхронизации:</span><span class="detail-value">${data.sync_status || '—'}</span></div>`;
            rows.forEach(([label, value]) => {
                html += `<div class="detail-item"><span class="detail-label">${label}:</span><span class="detail-value">${(value ?? 0)}</span></div>`;
            });
            html += '</div>';
            if (Object.keys(timings).length > 0) {
                html += '<div class="provider-info-card"><h4>Время выполнения правил (сек)</h4>';
                for (const [k, v] of Object.entries(timings)) {
                    const sec = (typeof v === 'number') ? v : parseFloat(v) || 0;
                    html += `<div class="detail-item"><span class="detail-label">${k}</span><span class="detail-value">${sec.toFixed(3)}</span></div>`;
                }
                html += '</div>';
            }
            body.innerHTML = html;
        })
        .catch(err => {
            console.error('summary error', err);
            body.innerHTML = '<div style="color: var(--error-red);">Ошибка загрузки сводки</div>';
        });
}

function closeRecoSummary() {
    document.getElementById('recoSummaryModal').style.display = 'none';
}

// ============================================================================
// Utility Functions
// ============================================================================

function toggleAccountInfo(providerId) {
    const content = document.getElementById(`account-info-${providerId}`);
    const chevron = document.getElementById(`chevron-${providerId}`);
    
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        chevron.classList.add('rotated');
    } else {
        content.style.display = 'none';
        chevron.classList.remove('rotated');
    }
}

function testConnection() {
    const selectedProvider = document.getElementById('provider_select').value;
    
    if (!selectedProvider) {
        showTestResult('Выберите провайдера', 'error');
        return;
    }
    
    const formData = {};
    const provider = providers[selectedProvider];
    
    provider.fields.forEach(field => {
        const element = document.getElementById(field.name);
        if (element) {
            formData[field.name] = element.value;
        }
    });
    
    for (const field of provider.fields) {
        if (field.required && !formData[field.name]) {
            showTestResult(`Заполните поле: ${field.label}`, 'error');
            return;
        }
    }
    
    showTestResult('Тестирование подключения...', 'info');
    
    const testEndpoint = selectedProvider === 'selectel' ? '/api/providers/selectel/test' : '/api/providers/beget/test';
    fetch(testEndpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let message = '✅ Подключение успешно установлено!';
            
            if (data.account_info) {
                const account = data.account_info;
                const accountName = account.name || account.customer_login || account.username || 'Unknown';
                const customerId = account.customer_id || account.id || '';
                
                if (customerId && customerId !== accountName) {
                    message = `✅ Подключение успешно! Аккаунт: ${accountName} (ID: ${customerId})`;
                } else {
                    message = `✅ Подключение успешно! Аккаунт: ${accountName}`;
                }
            }
            
            showTestResult(message, 'success');
        } else {
            let errorMessage = '❌ ' + (data.error || 'Ошибка подключения');
            
            if (data.error && data.error.includes('Authentication failed')) {
                errorMessage += '<br><br><strong>Возможные причины:</strong><br>• Проверьте правильность имени пользователя и пароля<br>• Убедитесь, что API доступ включен в панели управления<br>• Используйте пароль API, а не пароль от аккаунта';
            }
            
            showTestResult(errorMessage, 'error');
        }
    })
    .catch(error => {
        showTestResult('❌ Ошибка тестирования подключения', 'error');
        console.error('Connection test error:', error);
    });
}

function showTestResult(message, type) {
    const testDiv = document.getElementById('connectionTest');
    testDiv.innerHTML = message;
    testDiv.className = `connection-test-compact ${type}`;
    testDiv.style.display = 'block';
}

// ============================================================================
// Modal Helpers (kept inline for now, can be extracted later)
// ============================================================================

function resetModalToAddMode() {
    document.getElementById('providerForm').reset();
    document.querySelector('.modal-title').innerHTML = 
        '<i class="fa-solid fa-cloud" style="color: #1E40AF; margin-right: 0.5rem;"></i>Подключение облачного провайдера';
    
    const connectBtn = document.getElementById('connectBtn');
    connectBtn.innerHTML = 'Подключить';
    connectBtn.style.display = 'none';
    
    const testBtn = document.getElementById('testBtn');
    testBtn.style.display = 'none';
    
    const providerSelect = document.getElementById('provider_select');
    providerSelect.disabled = false;
    providerSelect.style.opacity = '1';
    providerSelect.style.cursor = 'pointer';
    
    document.getElementById('connectionTest').style.display = 'none';
    
    const existingEditId = document.getElementById('edit_connection_id');
    if (existingEditId) {
        existingEditId.remove();
    }
}

function showProviderModalForEdit(connectionData, providerType) {
    document.getElementById('providerModal').style.display = 'block';
    setModalToEditMode(connectionData);
    
    const providerSelect = document.getElementById('provider_select');
    providerSelect.value = providerType || connectionData.provider;
    changeProvider();
    
    const waitForFields = () => {
        const readyField = document.querySelector('input[name="api_key"], input[name="username"]');
        if (readyField) {
            fillEditForm(connectionData);
        } else {
            setTimeout(waitForFields, 50);
        }
    };
    waitForFields();
}

function setModalToEditMode(connectionData) {
    document.querySelector('.modal-title').innerHTML = 
        '<i class="fa-solid fa-edit" style="color: #1E40AF; margin-right: 0.5rem;"></i>Редактирование подключения';
    
    const connectBtn = document.getElementById('connectBtn');
    connectBtn.innerHTML = 'Сохранить изменения';
    connectBtn.style.display = 'none';
    
    const testBtn = document.getElementById('testBtn');
    testBtn.style.display = 'inline-block';
    
    const providerSelect = document.getElementById('provider_select');
    providerSelect.disabled = true;
    providerSelect.style.opacity = '0.6';
    providerSelect.style.cursor = 'not-allowed';
    
    const form = document.getElementById('providerForm');
    let editIdField = document.getElementById('edit_connection_id');
    if (!editIdField) {
        editIdField = document.createElement('input');
        editIdField.type = 'hidden';
        editIdField.id = 'edit_connection_id';
        editIdField.name = 'edit_connection_id';
        form.appendChild(editIdField);
    }
    editIdField.value = connectionData.id;
}

function fillEditForm(connectionData) {
    document.getElementById('connection_name').value = connectionData.connection_name || '';
    document.getElementById('description').value = connectionData.description || '';
    
    const provider = connectionData.provider;
    
    if (provider === 'beget') {
        const usernameField = document.querySelector('input[name="username"]');
        if (usernameField) usernameField.value = connectionData.username || '';
        
        const passwordField = document.querySelector('input[name="password"]');
        if (passwordField) {
            passwordField.value = connectionData.password || '';
            passwordField.placeholder = 'Введите новый пароль (оставьте пустым, чтобы не менять)';
        }
    } else if (provider === 'selectel') {
        const apiKeyField = document.querySelector('input[name="api_key"]');
        if (apiKeyField) {
            apiKeyField.value = connectionData.api_key || '';
        }
        
        const serviceUsernameField = document.querySelector('input[name="service_username"]');
        if (serviceUsernameField) {
            serviceUsernameField.value = connectionData.service_username || '';
        }
        
        const servicePasswordField = document.querySelector('input[name="service_password"]');
        if (servicePasswordField) {
            servicePasswordField.value = connectionData.service_password || '';
            servicePasswordField.placeholder = 'Введите новый пароль (оставьте пустым, чтобы не менять)';
        }
    }
    
    const autoSyncCheckbox = document.getElementById('auto_sync');
    if (autoSyncCheckbox) {
        autoSyncCheckbox.checked = connectionData.auto_sync !== false;
    }
    
    const collectStatsCheckbox = document.getElementById('collect_performance_stats');
    if (collectStatsCheckbox) {
        collectStatsCheckbox.checked = connectionData.collect_performance_stats !== false;
    }
    
    const syncIntervalSelect = document.getElementById('sync_interval');
    if (syncIntervalSelect && connectionData.sync_interval) {
        const intervalMap = {
            3600: 'hourly',
            86400: 'daily',
            604800: 'weekly',
            0: 'manual'
        };
        syncIntervalSelect.value = intervalMap[connectionData.sync_interval] || 'daily';
    }
    
    document.getElementById('connectionTest').style.display = 'block';
    document.getElementById('testBtn').style.display = 'inline-block';
    document.getElementById('connectBtn').style.display = 'inline-block';
}

// ============================================================================
// Initialize
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Form submission handler
    const form = document.getElementById('providerForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const editIdField = document.getElementById('edit_connection_id');
            const selectedProvider = document.getElementById('selected_provider').value;
            
            if (editIdField && editIdField.value) {
                const providerId = editIdField.value;
                const updateUrl = `/api/providers/${selectedProvider}/${providerId}/update`;
                
                const formData = new FormData(form);
                
                fetch(updateUrl, {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showFlashMessage('✅ Подключение обновлено успешно!', 'success');
                        closeProviderModal();
                        location.reload();
                    } else {
                        showFlashMessage('❌ Ошибка обновления: ' + (data.message || data.error), 'error');
                    }
                })
                .catch(error => {
                    showFlashMessage('❌ Ошибка обновления подключения', 'error');
                    console.error('Update error:', error);
                });
            } else {
                form.submit();
            }
        });
    }
    
    // Close modal on outside click
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('providerModal');
        if (event.target === modal) {
            closeProviderModal();
        }
        const recoModal = document.getElementById('recoSummaryModal');
        if (recoModal && event.target === recoModal) {
            closeRecoSummary();
        }
    });
    
    // Clear any stale success flash messages on page load if there are warnings
    // This handles cases where old success messages are still in the session
    setTimeout(() => {
        const existingFlashes = document.querySelectorAll('.flash-message.flash-success');
        const hasWarnings = document.querySelector('.sync-status.warning') !== null;
        
        if (hasWarnings && existingFlashes.length > 0) {
            // There are warnings on the page but stale success messages - clear them
            existingFlashes.forEach(flash => flash.remove());
        }
    }, 100);
});

