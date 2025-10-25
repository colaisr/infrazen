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
    
    // Choose icon based on type
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    else if (type === 'error') icon = 'exclamation-circle';
    else if (type === 'warning') icon = 'exclamation-triangle';
    
    flashDiv.innerHTML = `
        <i class="fa-solid fa-${icon}"></i>
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
 * Update provider card UI after sync completes
 * @param {string|number} providerId - The provider ID  
 * @param {Object} syncData - Sync result data
 * @param {boolean} isPartialSync - Whether this was a partial sync
 */
function updateProviderCardAfterSync(providerId, syncData, isPartialSync) {
    // Find the provider card by ID (format: "provider-selectel-2" or just the numeric ID)
    let providerCard = document.getElementById(`provider-${providerId}`);
    
    // If not found, try finding by button onclick
    if (!providerCard) {
        const syncButton = document.querySelector(`button[onclick*="'${providerId}'"]`);
        if (syncButton) {
            providerCard = syncButton.closest('.connection-card');
        }
    }
    
    if (!providerCard) {
        console.warn('Could not find provider card for ID:', providerId);
        return;
    }
    
    console.log('Updating provider card:', providerId, 'isPartialSync:', isPartialSync);
    
    // Update sync status badge
    const syncStatus = providerCard.querySelector('.sync-status');
    if (syncStatus) {
        const now = new Date().toLocaleString('ru-RU', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
        
        if (isPartialSync) {
            syncStatus.className = 'sync-status warning';
            syncStatus.innerHTML = `
                <i class="fa-solid fa-exclamation-triangle"></i>
                <span>⚠️ Частичная синхронизация ${now}</span>
            `;
            
            // Add or update error message
            let errorMsg = providerCard.querySelector('.sync-error-message');
            if (!errorMsg) {
                errorMsg = document.createElement('div');
                errorMsg.className = 'sync-error-message';
                syncStatus.parentElement.insertBefore(errorMsg, syncStatus.nextSibling);
            }
            
            // Extract the actual error from the message (remove the prefix)
            let errorText = syncData.message || 'OpenStack authentication failed';
            if (errorText.includes(' - VMs lack')) {
                // Extract just the important part
                errorText = 'OpenStack authentication failed - VMs have limited details. Check service user credentials.';
            }
            
            errorMsg.innerHTML = `
                <i class="fa-solid fa-info-circle"></i>
                <span>${errorText}</span>
            `;
        } else {
            syncStatus.className = 'sync-status success';
            syncStatus.innerHTML = `
                <i class="fa-solid fa-check-circle"></i>
                <span>Синхронизирован ${now}</span>
            `;
            
            // Remove error message if it exists
            const errorMsg = providerCard.querySelector('.sync-error-message');
            if (errorMsg) {
                errorMsg.remove();
            }
        }
    }
    
    // Update cost if available
    if (syncData.total_daily_cost !== undefined) {
        const costPrimary = providerCard.querySelector('.cost-primary .cost-amount');
        if (costPrimary) {
            costPrimary.textContent = `${syncData.total_daily_cost.toFixed(1)} ₽`;
        }
        
        const costSecondary = providerCard.querySelector('.cost-amount-secondary');
        if (costSecondary && syncData.total_monthly_cost) {
            costSecondary.textContent = `${(syncData.total_daily_cost * 30).toFixed(1)} ₽`;
        }
    }
    
    // Update resource count if available
    if (syncData.resources_synced !== undefined) {
        const resourceCount = providerCard.querySelector('.resource-count');
        if (resourceCount) {
            resourceCount.textContent = `${syncData.resources_synced} ресурсов`;
        }
    }
}

/**
 * Synchronize a provider's resources
 * @param {string|number} providerId - The provider ID (numeric, for API)
 * @param {string} providerType - The provider type (beget, selectel, etc.)
 * @param {HTMLElement} button - The button element that triggered the sync
 * @param {Function} onSuccess - Optional callback on success
 * @param {string} fullProviderId - The full provider ID (e.g., "selectel-2", for UI updates)
 */
function syncProvider(providerId, providerType, button, onSuccess, fullProviderId) {
    const originalText = button.innerHTML;
    const originalColor = button.style.color;
    
    // Show loading state
    button.disabled = true;
    button.classList.add('loading');
    button.style.color = 'white'; // Ensure text is visible on blue background
    button.innerHTML = '<i class="fa-solid fa-arrows-rotate fa-spin"></i><span style="margin-left: 0.5rem;">Синхронизация...</span>';
    
    // Create AbortController for timeout (120 seconds for statistics collection)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout
    
    // Make sync request with extended timeout
    fetch(`/api/providers/${providerType}/${providerId}/sync`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        signal: controller.signal
    })
    .then(response => {
        clearTimeout(timeoutId); // Clear timeout on successful response
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Check if this was a partial sync (OpenStack auth failed)
            const isPartialSync = data.openstack_auth_ok === false || (data.message && data.message.includes('⚠️'));
            
            if (isPartialSync) {
                // Show warning state for partial sync
                button.innerHTML = '<i class="fa-solid fa-exclamation-triangle"></i><span style="margin-left: 0.5rem;">Частичная синхронизация</span>';
                button.style.background = '#f59e0b';
                button.style.borderColor = '#f59e0b';
                button.style.color = 'white';
                
                // Show warning message with details
                const warningMessage = data.message || 'Синхронизация завершена с предупреждениями';
                showFlashMessage('⚠️ ' + warningMessage, 'warning');
                
                // Update the card UI to show warning status (use full ID if available)
                const cardId = fullProviderId || `${providerType}-${providerId}`;
                updateProviderCardAfterSync(cardId, data, true);
            } else {
                // Show full success state
                button.innerHTML = '<i class="fa-solid fa-check"></i><span style="margin-left: 0.5rem;">Синхронизировано</span>';
                button.style.background = 'var(--success-green)';
                button.style.borderColor = 'var(--success-green)';
                button.style.color = 'white';
                
                showFlashMessage('✅ Синхронизация завершена успешно!', 'success');
                
                // Update the card UI to show success status (use full ID if available)
                const cardId = fullProviderId || `${providerType}-${providerId}`;
                updateProviderCardAfterSync(cardId, data, false);
            }
            
            // Execute callback without reload
            if (onSuccess && typeof onSuccess === 'function') {
                setTimeout(() => onSuccess(data), 1500);
            }
            // NO MORE PAGE RELOAD - just update UI dynamically
            
            // Reset button after 3 seconds
            setTimeout(() => {
                button.disabled = false;
                button.classList.remove('loading');
                button.innerHTML = originalText;
                button.style.background = '';
                button.style.borderColor = '';
                button.style.color = originalColor;
            }, 3000);
        } else {
            throw new Error(data.error || 'Sync failed');
        }
    })
    .catch(error => {
        clearTimeout(timeoutId); // Clear timeout on error
        console.error('Sync error:', error);
        
        // Check if it was a timeout
        const isTimeout = error.name === 'AbortError';
        const errorMessage = isTimeout 
            ? 'Превышено время ожидания (>120 сек) - попробуйте отключить сбор статистики'
            : error.message;
        
        // Show error state
        button.innerHTML = '<i class="fa-solid fa-exclamation-triangle"></i><span style="margin-left: 0.5rem;">Ошибка</span>';
        button.style.background = 'var(--error-red)';
        button.style.borderColor = 'var(--error-red)';
        button.style.color = 'white';
        
        showFlashMessage('❌ Ошибка синхронизации: ' + errorMessage, 'error');
        
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
 * Wrapper function for inline onclick handlers
 * Extracts the button reference and calls syncProvider
 */
function syncConnection(connectionId, providerType) {
    const numericId = connectionId.includes('-') ? connectionId.split('-')[1] : connectionId;
    const button = event.target.closest('button');
    
    // Pass both numeric ID (for API) and full ID (for card updates)
    syncProvider(numericId, providerType, button, null, connectionId);
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
    
    // Create AbortController for timeout (180 seconds for multiple providers with stats)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000); // 180 second timeout
    
    // Make complete sync request with extended timeout
    fetch('/api/complete-sync', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            sync_type: 'manual'
        }),
        signal: controller.signal
    })
    .then(response => {
        clearTimeout(timeoutId); // Clear timeout on response
        return response.json();
    })
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
            
            // Reset button state
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 3000);
            
            // TODO: Update all provider cards dynamically instead of reload
            // For now, just show the success message - user can manually refresh if needed
        } else {
            showFlashMessage('❌ Ошибка полной синхронизации: ' + (data.error || data.message), 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        clearTimeout(timeoutId); // Clear timeout on error
        
        const isTimeout = error.name === 'AbortError';
        const errorMessage = isTimeout
            ? 'Превышено время ожидания (>180 сек) - синхронизация может продолжаться на сервере'
            : error.message || 'Неизвестная ошибка';
        
        showFlashMessage('❌ Ошибка полной синхронизации: ' + errorMessage, 'error');
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

