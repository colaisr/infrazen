/**
 * InfraZen - Main JavaScript Utilities
 * Common functions used across multiple pages
 */

// ============================================================================
// Flash Messages
// ============================================================================

/**
 * Display a flash message to the user
 * @param {string} message - The message to display (can include HTML)
 * @param {string} type - Message type: 'success' or 'error'
 */
function showFlashMessage(message, type) {
    // Clear existing flash messages first
    const existingContainer = document.querySelector('.flash-messages');
    if (existingContainer) {
        existingContainer.remove();
    }
    
    // Create flash message element
    const flashDiv = document.createElement('div');
    flashDiv.className = `flash-message flash-${type}`;
    flashDiv.innerHTML = `
        <i class="fa-solid fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
        <button class="flash-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // Add to flash messages container
    let container = document.querySelector('.flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }
    
    container.appendChild(flashDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (flashDiv.parentElement) {
            flashDiv.remove();
        }
    }, 5000);
}

// ============================================================================
// Provider Sync Operations
// ============================================================================

/**
 * Synchronize a provider's resources
 * @param {string|number} providerId - The provider ID
 * @param {string} providerType - The provider type (beget, selectel, etc.)
 * @param {HTMLElement} button - The button element that triggered the sync
 * @param {Function} onSuccess - Optional callback on success
 */
function syncProvider(providerId, providerType, button, onSuccess) {
    const originalText = button.innerHTML;
    
    // Show loading state
    button.disabled = true;
    button.classList.add('loading');
    button.innerHTML = '<i class="fa-solid fa-arrows-rotate fa-spin"></i><span>Синхронизация...</span>';
    
    // Make sync request
    fetch(`/api/providers/${providerType}/${providerId}/sync`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success state
            button.innerHTML = '<i class="fa-solid fa-check"></i><span>Синхронизировано</span>';
            button.style.background = 'var(--success-green)';
            button.style.borderColor = 'var(--success-green)';
            button.style.color = 'white';
            
            showFlashMessage('✅ Синхронизация завершена успешно!', 'success');
            
            // Execute callback or reload
            if (onSuccess && typeof onSuccess === 'function') {
                setTimeout(() => onSuccess(data), 1500);
            } else {
                setTimeout(() => window.location.reload(), 2000);
            }
        } else {
            throw new Error(data.error || 'Sync failed');
        }
    })
    .catch(error => {
        console.error('Sync error:', error);
        
        // Show error state
        button.innerHTML = '<i class="fa-solid fa-exclamation-triangle"></i><span>Ошибка</span>';
        button.style.background = 'var(--error-red)';
        button.style.borderColor = 'var(--error-red)';
        button.style.color = 'white';
        
        showFlashMessage('❌ Ошибка синхронизации: ' + error.message, 'error');
        
        // Reset after 3 seconds
        setTimeout(() => {
            button.disabled = false;
            button.classList.remove('loading');
            button.innerHTML = originalText;
            button.style.background = '';
            button.style.borderColor = '';
            button.style.color = '';
        }, 3000);
    });
}

/**
 * Start a complete sync of all providers
 * @param {HTMLElement} button - The button element that triggered the sync
 */
function startCompleteSync(button) {
    const originalText = button.innerHTML;
    
    // Show loading state
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Синхронизация всех...</span>';
    button.disabled = true;
    
    // Make complete sync request
    fetch('/api/complete-sync', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            sync_type: 'manual'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message with aggregated results
            let message = `✅ Полная синхронизация завершена!<br>`;
            message += `📊 Провайдеров: ${data.total_providers_synced}<br>`;
            message += `💰 Общая стоимость: ${data.total_daily_cost.toFixed(2)} ₽/день<br>`;
            message += `📦 Ресурсов: ${data.total_resources_found}`;
            
            if (data.cost_by_provider && Object.keys(data.cost_by_provider).length > 0) {
                message += `<br><br>📈 По провайдерам:<br>`;
                for (const [provider, cost] of Object.entries(data.cost_by_provider)) {
                    message += `• ${provider}: ${cost.toFixed(2)} ₽/день<br>`;
                }
            }
            
            showFlashMessage(message, 'success');
            
            // Reload page to show updated data
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        } else {
            showFlashMessage('❌ Ошибка полной синхронизации: ' + (data.error || data.message), 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        showFlashMessage('❌ Ошибка полной синхронизации', 'error');
        console.error('Complete sync error:', error);
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Toggle password visibility
 * @param {string} fieldName - The ID of the password field
 */
function togglePasswordVisibility(fieldName) {
    const passwordField = document.getElementById(fieldName);
    const eyeIcon = document.getElementById(`eye-${fieldName}`);
    
    if (passwordField.type === 'password') {
        passwordField.type = 'text';
        eyeIcon.className = 'fa-solid fa-eye-slash';
    } else {
        passwordField.type = 'password';
        eyeIcon.className = 'fa-solid fa-eye';
    }
}

/**
 * Set up event delegation for sync buttons
 * Allows dynamic buttons to work without inline onclick
 */
function initializeSyncButtons() {
    document.addEventListener('click', function(e) {
        const syncBtn = e.target.closest('[data-sync-provider]');
        if (syncBtn) {
            e.preventDefault();
            const providerId = syncBtn.dataset.syncProvider;
            const providerType = syncBtn.dataset.providerType;
            
            if (providerId && providerType) {
                syncProvider(providerId, providerType, syncBtn);
            }
        }
        
        const completeSyncBtn = e.target.closest('[data-complete-sync]');
        if (completeSyncBtn) {
            e.preventDefault();
            startCompleteSync(completeSyncBtn);
        }
    });
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeSyncButtons);
} else {
    initializeSyncButtons();
}

