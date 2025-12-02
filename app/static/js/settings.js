/**
 * InfraZen - Settings Page JavaScript
 * Handles user account settings, password management, and Google OAuth linking
 */

// ============================================================================
// State Management
// ============================================================================

let userDetails = null;

// Get Google Client ID from template data
let googleClientId = '';
if (window.INFRAZEN_DATA && window.INFRAZEN_DATA.googleClientId) {
    googleClientId = window.INFRAZEN_DATA.googleClientId;
}

// ============================================================================
// User Details Loading
// ============================================================================

function loadUserDetails() {
    fetch('/api/auth/user-details')
        .then(response => {
            if (response.status === 401) {
                // Authentication error - redirect to login
                window.location.href = '/api/auth/login';
                return;
            }
            return response.json();
        })
        .then(data => {
            if (data && data.success) {
                userDetails = data.user;
                updateAccountInfo(userDetails);
                updateLoginMethods(userDetails);
                updatePasswordManagement(userDetails);
                updatePreferences(userDetails);
                loadOrganizationManagement(); // Load organization management
            } else if (data && data.redirect) {
                // Server requested redirect (e.g., user account no longer exists)
                showMessage(data.error || 'Session expired', 'error');
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 2000);
            } else {
                showMessage('Failed to load user details', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('Failed to load user details', 'error');
        });
}

// ============================================================================
// UI Update Functions
// ============================================================================

function updateAccountInfo(user) {
    document.getElementById('accountCreated').textContent = 
        new Date(user.created_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    
    // Update email confirmation badge
    const emailBadge = document.getElementById('emailStatusBadge');
    const sendBtn = document.getElementById('sendConfirmationBtn');
    const isEmailConfirmed = user.is_email_confirmed;
    
    if (isEmailConfirmed) {
        emailBadge.innerHTML = '<i class="fa-solid fa-check-circle"></i> Verified';
        emailBadge.style.color = '#10b981';
        emailBadge.style.fontWeight = '500';
        sendBtn.style.display = 'none';
    } else {
        emailBadge.innerHTML = '<i class="fa-solid fa-exclamation-circle"></i> Not Verified';
        emailBadge.style.color = '#f59e0b';
        emailBadge.style.fontWeight = '500';
        sendBtn.style.display = 'inline-block';
    }
}

function updateLoginMethods(user) {
    // Google OAuth status
    const hasGoogle = user.google_id !== null;
    const googleStatus = document.getElementById('googleStatus');
    const googleBadge = document.getElementById('googleBadge');
    const googleMethod = document.getElementById('googleLoginMethod');
    
    if (hasGoogle) {
        googleStatus.textContent = 'Connected to Google account';
        googleBadge.className = 'method-badge badge-enabled';
        googleBadge.textContent = 'Enabled';
        googleMethod.classList.remove('clickable');
    } else {
        googleStatus.textContent = 'Not connected - Click to connect';
        googleBadge.className = 'method-badge badge-disabled';
        googleBadge.textContent = 'Connect';
        googleMethod.classList.add('clickable');
    }
    
    // Password status
    const hasPassword = user.has_password;
    const passwordStatus = document.getElementById('passwordStatus');
    const passwordBadge = document.getElementById('passwordBadge');
    
    if (hasPassword) {
        passwordStatus.textContent = 'Password is set';
        passwordBadge.className = 'method-badge badge-enabled';
        passwordBadge.textContent = 'Enabled';
    } else {
        passwordStatus.textContent = 'No password set';
        passwordBadge.className = 'method-badge badge-disabled';
        passwordBadge.textContent = 'Disabled';
    }
    
    // Current login method
    const loginMethod = user.current_login_method || 'unknown';
    document.getElementById('currentLoginMethod').innerHTML = 
        `Current session: <strong>${loginMethod === 'google' ? 'Google OAuth' : loginMethod === 'password' ? 'Username & Password' : 'Unknown'}</strong>`;
}

function updatePreferences(user) {
    document.getElementById('userTimezone').textContent = user.timezone || 'UTC';
    document.getElementById('userCurrency').textContent = user.currency || 'RUB';
    document.getElementById('userLanguage').textContent = user.language || 'ru';
}

// ============================================================================
// Google OAuth Integration
// ============================================================================

function handleGoogleConnect() {
    // Check if user already has Google connected
    const hasGoogle = userDetails && userDetails.google_id !== null;
    
    if (hasGoogle) {
        showMessage('Google account is already connected', 'info');
        return;
    }
    
    // Show the Google OAuth modal
    showGoogleConnectModal();
}

function showGoogleConnectModal() {
    // Create modal HTML
    const modalHTML = `
        <div id="googleConnectModal" class="modal-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;">
            <div class="modal-content" style="background: white; padding: 2rem; border-radius: 12px; max-width: 400px; width: 90%; text-align: center; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);">
                <h3 style="margin-bottom: 1rem; color: #1e293b;">Connect Google Account</h3>
                <p style="margin-bottom: 1.5rem; color: #64748b;">Sign in with Google to link your account</p>
                
                <!-- Google Sign-In Button (same as login) -->
                <div id="g_id_onload_connect"
                     data-client_id="${googleClientId}"
                     data-context="signin"
                     data-ux_mode="popup"
                     data-callback="handleGoogleConnectResponse"
                     data-auto_prompt="false">
                </div>
                
                <div class="g_id_signin"
                     data-type="standard"
                     data-shape="rectangular"
                     data-theme="outline"
                     data-text="signin_with"
                     data-size="large"
                     data-logo_alignment="left"
                     data-width="100%">
                </div>
                
                <button onclick="closeGoogleConnectModal()" style="margin-top: 1rem; background: #f1f5f9; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; color: #64748b;">
                    Cancel
                </button>
            </div>
        </div>
    `;
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Initialize Google Sign-In for the modal
    if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
        google.accounts.id.renderButton(document.querySelector('#googleConnectModal .g_id_signin'), {
            theme: 'outline',
            size: 'large',
            width: '100%',
            text: 'signin_with'
        });
    }
}

function closeGoogleConnectModal() {
    const modal = document.getElementById('googleConnectModal');
    if (modal) {
        modal.remove();
    }
}

function handleGoogleConnectResponse(response) {
    // Close the modal first
    closeGoogleConnectModal();
    
    // Show loading state
    const googleStatus = document.getElementById('googleStatus');
    const googleBadge = document.getElementById('googleBadge');
    
    googleStatus.textContent = 'Connecting...';
    googleBadge.textContent = 'Connecting';
    
    // Send the credential to our backend to link the account
    fetch('/api/auth/link-google', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            credential: response.credential
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Google account connected successfully!', 'success');
            // Reload user details to update the UI
            loadUserDetails();
        } else {
            showMessage('Failed to connect Google account: ' + data.error, 'error');
            // Reset UI state
            googleStatus.textContent = 'Not connected - Click to connect';
            googleBadge.textContent = 'Connect';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Failed to connect Google account', 'error');
        // Reset UI state
        googleStatus.textContent = 'Not connected - Click to connect';
        googleBadge.textContent = 'Connect';
    });
}

// ============================================================================
// Password Management
// ============================================================================

function updatePasswordManagement(user) {
    const container = document.getElementById('passwordManagementContent');
    const hasPassword = user.has_password;
    
    if (hasPassword) {
        // User has a password - show change password form
        container.innerHTML = `
            <div class="has-password-message">
                <i class="fa-solid fa-check-circle"></i>
                You have a password set. You can change it below.
            </div>
            <form class="password-form" onsubmit="changePassword(event)">
                <!-- Hidden username field for accessibility -->
                <input type="email" name="username" value="${user.email}" style="display: none;" autocomplete="username">
                <div class="form-group">
                    <label for="currentPassword">Current Password</label>
                    <input type="password" id="currentPassword" name="currentPassword" required autocomplete="current-password">
                </div>
                <div class="form-group">
                    <label for="newPassword">New Password</label>
                    <input type="password" id="newPassword" name="newPassword" required 
                           oninput="checkPasswordStrength()" autocomplete="new-password">
                    <div class="password-requirements">
                        <div>Password must:</div>
                        <ul>
                            <li id="req-length">Be at least 6 characters long</li>
                        </ul>
                    </div>
                </div>
                <div class="form-group">
                    <label for="confirmPassword">Confirm New Password</label>
                    <input type="password" id="confirmPassword" name="confirmPassword" required 
                           oninput="checkPasswordMatch()" autocomplete="new-password">
                    <small id="passwordMatchMessage" style="color: #dc2626; display: none;">Passwords do not match</small>
                </div>
                <button type="submit" class="btn btn-primary" id="changePasswordBtn">
                    <i class="fa-solid fa-key"></i> Change Password
                </button>
            </form>
        `;
    } else {
        // User doesn't have a password - show set password form
        container.innerHTML = `
            <div class="no-password-message">
                <i class="fa-solid fa-exclamation-triangle"></i>
                You don't have a password set. Set a password to enable username/password login.
            </div>
            <form class="password-form" onsubmit="setPassword(event)">
                <!-- Hidden username field for accessibility -->
                <input type="email" name="username" value="${user.email}" style="display: none;" autocomplete="username">
                <div class="form-group">
                    <label for="newPassword">New Password</label>
                    <input type="password" id="newPassword" name="newPassword" required 
                           oninput="checkPasswordStrength()" autocomplete="new-password">
                    <div class="password-requirements">
                        <div>Password must:</div>
                        <ul>
                            <li id="req-length">Be at least 6 characters long</li>
                        </ul>
                    </div>
                </div>
                <div class="form-group">
                    <label for="confirmPassword">Confirm Password</label>
                    <input type="password" id="confirmPassword" name="confirmPassword" required 
                           oninput="checkPasswordMatch()" autocomplete="new-password">
                    <small id="passwordMatchMessage" style="color: #dc2626; display: none;">Passwords do not match</small>
                </div>
                <button type="submit" class="btn btn-primary" id="setPasswordBtn">
                    <i class="fa-solid fa-lock"></i> Set Password
                </button>
            </form>
        `;
    }
}

function checkPasswordStrength() {
    const password = document.getElementById('newPassword').value;
    const lengthReq = document.getElementById('req-length');
    
    if (password.length >= 6) {
        lengthReq.classList.add('met');
    } else {
        lengthReq.classList.remove('met');
    }
}

function checkPasswordMatch() {
    const password = document.getElementById('newPassword').value;
    const confirm = document.getElementById('confirmPassword').value;
    const message = document.getElementById('passwordMatchMessage');
    
    if (confirm && password !== confirm) {
        message.style.display = 'block';
    } else {
        message.style.display = 'none';
    }
}

function setPassword(event) {
    event.preventDefault();
    
    const password = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (password !== confirmPassword) {
        showMessage('Passwords do not match', 'error');
        return;
    }
    
    if (password.length < 6) {
        showMessage('Password must be at least 6 characters', 'error');
        return;
    }
    
    const btn = document.getElementById('setPasswordBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Setting password...';
    
    fetch('/api/auth/set-password', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            password: password,
            confirm_password: confirmPassword
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Password set successfully! You can now login with username/password.', 'success');
            // Reload user details to update the UI
            setTimeout(() => {
                loadUserDetails();
            }, 1500);
        } else {
            showMessage(data.error || 'Failed to set password', 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-lock"></i> Set Password';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Failed to set password', 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-lock"></i> Set Password';
    });
}

function changePassword(event) {
    event.preventDefault();
    
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (newPassword !== confirmPassword) {
        showMessage('Passwords do not match', 'error');
        return;
    }
    
    if (newPassword.length < 6) {
        showMessage('Password must be at least 6 characters', 'error');
        return;
    }
    
    const btn = document.getElementById('changePasswordBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Changing password...';
    
    fetch('/api/auth/change-password', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            current_password: currentPassword,
            password: newPassword,
            confirm_password: confirmPassword
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Password changed successfully!', 'success');
            // Clear form
            event.target.reset();
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-key"></i> Change Password';
        } else {
            showMessage(data.error || 'Failed to change password', 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-key"></i> Change Password';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Failed to change password', 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-key"></i> Change Password';
    });
}

// ============================================================================
// Message Display
// ============================================================================

function showMessage(message, type) {
    const container = document.getElementById('messageContainer');
    const messageEl = document.createElement('div');
    messageEl.className = `message ${type}`;
    messageEl.innerHTML = `
        <i class="fa-solid fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        ${message}
    `;
    
    container.appendChild(messageEl);
    
    setTimeout(() => {
        messageEl.remove();
    }, 5000);
}

// ============================================================================
// Provider Preferences for Recommendations
// ============================================================================

function loadProviderPreferences() {
    fetch('/api/auth/provider-preferences')
        .then(response => {
            if (response.status === 401) {
                window.location.href = '/api/auth/login';
                return;
            }
            return response.json();
        })
        .then(data => {
            if (data && data.success) {
                displayProviderPreferences(data.providers);
            } else {
                showMessage('Failed to load provider preferences', 'error');
            }
        })
        .catch(error => {
            console.error('Error loading provider preferences:', error);
            showMessage('Failed to load provider preferences', 'error');
        });
}

function displayProviderPreferences(providers) {
    const container = document.getElementById('providerPreferencesList');
    
    if (!providers || providers.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #64748b;">No providers available</p>';
        return;
    }
    
    container.innerHTML = '';
    
    providers.forEach(provider => {
        const item = document.createElement('div');
        item.className = 'provider-preference-item';
        item.dataset.providerType = provider.provider_type;
        
        const logoHtml = provider.logo_url 
            ? `<img src="${provider.logo_url}" alt="${provider.display_name}" class="provider-logo">`
            : `<div class="provider-logo-placeholder">${provider.display_name.substring(0, 2).toUpperCase()}</div>`;
        
        item.innerHTML = `
            <div class="provider-info">
                ${logoHtml}
                <span class="provider-name">${provider.display_name}</span>
            </div>
            <label class="switch">
                <input type="checkbox" ${provider.is_enabled ? 'checked' : ''} 
                       onchange="toggleProviderPreference('${provider.provider_type}', this.checked)">
                <span class="slider"></span>
            </label>
        `;
        
        container.appendChild(item);
    });
}

function toggleProviderPreference(providerType, isEnabled) {
    fetch('/api/auth/provider-preferences', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            provider_type: providerType,
            is_enabled: isEnabled
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const action = isEnabled ? 'включен' : 'отключен';
            showMessage(`Провайдер ${action} для рекомендаций`, 'success');
        } else {
            showMessage('Failed to update provider preference: ' + data.error, 'error');
            // Revert the toggle on error
            const checkbox = document.querySelector(`[data-provider-type="${providerType}"] input[type="checkbox"]`);
            if (checkbox) {
                checkbox.checked = !isEnabled;
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Failed to update provider preference', 'error');
        // Revert the toggle on error
        const checkbox = document.querySelector(`[data-provider-type="${providerType}"] input[type="checkbox"]`);
        if (checkbox) {
            checkbox.checked = !isEnabled;
        }
    });
}

// ============================================================================
// Clear All Recommendations
// ============================================================================

async function clearAllRecommendations() {
    // Confirm action
    const confirmed = confirm(
        'Вы уверены, что хотите удалить ВСЕ рекомендации?\n\n' +
        'Это действие нельзя отменить. При следующей синхронизации система создаст новые рекомендации на основе актуальных данных.\n\n' +
        'Удалить все рекомендации?'
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch('/api/recommendations/clear-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Ошибка при удалении рекомендаций');
        }
        
        const result = await response.json();
        
        // Show success message
        showMessage(result.message || `Успешно удалено ${result.deleted_count} рекомендаций`, 'success');
        
    } catch (error) {
        console.error('Error clearing recommendations:', error);
        showMessage('Ошибка при удалении рекомендаций: ' + error.message, 'error');
    }
}

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    loadUserDetails();
    loadProviderPreferences();
    
    // Clear all recommendations button
    const clearAllBtn = document.getElementById('clearAllRecommendations');
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', clearAllRecommendations);
    }
});

// ============================================================================
// Email Confirmation
// ============================================================================

function sendConfirmationEmail() {
    const btn = document.getElementById('sendConfirmationBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    
    fetch('/api/auth/send-confirmation-email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(data.message || 'Confirmation email sent! Please check your inbox.', 'success');
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Email Sent';
            // Keep button disabled for 60 seconds to prevent spam
            setTimeout(() => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-envelope"></i> Send Confirmation Email';
            }, 60000);
        } else {
            showMessage(data.error || 'Failed to send confirmation email', 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-envelope"></i> Send Confirmation Email';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Failed to send confirmation email', 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-envelope"></i> Send Confirmation Email';
    });
}

// ============================================================================
// Organization Management
// ============================================================================

let currentOrganization = null;
let organizationMembers = [];
let organizationInvitations = [];

function loadOrganizationManagement() {
    // Get current organization ID from session or API
    fetch('/api/organizations')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.organizations && data.organizations.length > 0) {
                // Find current organization
                const currentOrg = data.organizations.find(org => org.is_current) || data.organizations[0];
                if (currentOrg) {
                    loadOrganizationDetails(currentOrg.id);
                } else {
                    showOrganizationError('Не найдена активная организация');
                }
            } else {
                showOrganizationError('Не найдено организаций');
            }
        })
        .catch(error => {
            console.error('Error loading organizations:', error);
            showOrganizationError('Ошибка при загрузке организаций');
        });
}

function loadOrganizationDetails(orgId) {
    fetch(`/api/organizations/${orgId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentOrganization = data.organization;
                organizationMembers = data.organization.members || [];
                displayOrganizationManagement(data.organization);
                loadOrganizationInvitations(orgId);
            } else {
                showOrganizationError(data.error || 'Не удалось загрузить информацию об организации');
            }
        })
        .catch(error => {
            console.error('Error loading organization details:', error);
            showOrganizationError('Ошибка при загрузке информации об организации');
        });
}

function loadOrganizationInvitations(orgId) {
    fetch(`/api/organizations/${orgId}/invitations`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                organizationInvitations = data.invitations || [];
                displayInvitations(organizationInvitations);
            }
        })
        .catch(error => {
            console.error('Error loading invitations:', error);
        });
}

function displayOrganizationManagement(org) {
    const container = document.getElementById('organizationManagementContent');
    if (!container) return;
    
    const isOwner = org.role === 'owner';
    
    let html = `
        <div class="organization-info">
            <div class="org-details-section">
                <h4>Информация об организации</h4>
                <div class="info-grid">
                    <div class="info-item">
                        <label>Название организации</label>
                        <div class="info-value">
                            ${isOwner ? `
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <input type="text" id="orgNameInput" value="${escapeHtml(org.name)}" class="form-input" style="flex: 1;">
                                    <button id="saveOrgNameBtn" class="btn btn-primary" onclick="saveOrganizationName()">
                                        <i class="fa-solid fa-save"></i> Сохранить
                                    </button>
                                </div>
                            ` : `
                                <span>${escapeHtml(org.name)}</span>
                            `}
                        </div>
                    </div>
                    <div class="info-item">
                        <label>Ваша роль</label>
                        <div class="info-value">
                            <span class="role-badge role-${org.role}">${getRoleLabel(org.role)}</span>
                        </div>
                    </div>
                    <div class="info-item">
                        <label>Участников</label>
                        <div class="info-value">${org.member_count || 0}</div>
                    </div>
                </div>
            </div>
            
            <div class="org-members-section" style="margin-top: 2rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h4>Участники</h4>
                    ${isOwner ? `
                        <button class="btn btn-primary" onclick="showInviteMemberModal()">
                            <i class="fa-solid fa-user-plus"></i> Пригласить участника
                        </button>
                    ` : ''}
                </div>
                <div id="membersList">
                    ${renderMembersList(org.members || [])}
                </div>
            </div>
            
            <div class="org-invitations-section" style="margin-top: 2rem;">
                <h4>Приглашения</h4>
                <div id="invitationsList">
                    ${renderInvitationsList(organizationInvitations)}
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

function renderMembersList(members) {
    if (members.length === 0) {
        return '<p style="color: var(--text-secondary);">Нет участников</p>';
    }
    
    const isOwner = currentOrganization && currentOrganization.role === 'owner';
    
    return `
        <div class="members-table">
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 2px solid var(--border-light);">
                        <th style="text-align: left; padding: 0.75rem; font-weight: 600;">Участник</th>
                        <th style="text-align: left; padding: 0.75rem; font-weight: 600;">Роль</th>
                        <th style="text-align: left; padding: 0.75rem; font-weight: 600;">Дата присоединения</th>
                        ${isOwner ? '<th style="text-align: right; padding: 0.75rem; font-weight: 600;">Действия</th>' : ''}
                    </tr>
                </thead>
                <tbody>
                    ${members.map(member => `
                        <tr style="border-bottom: 1px solid var(--border-light);">
                            <td style="padding: 0.75rem;">
                                <div style="display: flex; align-items: center; gap: 0.75rem;">
                                    <div class="user-avatar-small" style="width: 32px; height: 32px; border-radius: 50%; background: var(--primary-blue); color: white; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 0.75rem;">
                                        ${member.picture ? `<img src="${escapeHtml(member.picture)}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">` : (member.name ? member.name.charAt(0).toUpperCase() : member.email.charAt(0).toUpperCase())}
                                    </div>
                                    <div>
                                        <div style="font-weight: 500;">${escapeHtml(member.name || member.email)}</div>
                                        <div style="font-size: 0.875rem; color: var(--text-secondary);">${escapeHtml(member.email)}</div>
                                    </div>
                                </div>
                            </td>
                            <td style="padding: 0.75rem;">
                                ${isOwner && !member.is_owner ? `
                                    <select class="form-select" onchange="changeMemberRole(${member.user_id}, this.value)" style="padding: 0.25rem 0.5rem;">
                                        <option value="viewer" ${member.role === 'viewer' ? 'selected' : ''}>Наблюдатель</option>
                                        <option value="editor" ${member.role === 'editor' ? 'selected' : ''}>Редактор</option>
                                        <option value="owner" ${member.role === 'owner' ? 'selected' : ''} disabled>Владелец</option>
                                    </select>
                                ` : `
                                    <span class="role-badge role-${member.role}">${getRoleLabel(member.role)}</span>
                                `}
                            </td>
                            <td style="padding: 0.75rem; color: var(--text-secondary);">
                                ${member.joined_at ? new Date(member.joined_at).toLocaleDateString('ru-RU') : '-'}
                            </td>
                            ${isOwner ? `
                                <td style="padding: 0.75rem; text-align: right;">
                                    ${!member.is_owner ? `
                                        <button class="btn btn-danger btn-sm" onclick="removeMember(${member.user_id}, '${escapeHtml(member.name || member.email)}')" style="padding: 0.25rem 0.75rem; font-size: 0.875rem;">
                                            <i class="fa-solid fa-user-minus"></i> Удалить
                                        </button>
                                    ` : '<span style="color: var(--text-secondary);">-</span>'}
                                </td>
                            ` : ''}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function renderInvitationsList(invitations) {
    if (!invitations || invitations.length === 0) {
        return '<p style="color: var(--text-secondary);">Нет активных приглашений</p>';
    }
    
    const isOwner = currentOrganization && currentOrganization.role === 'owner';
    
    return `
        <div class="invitations-list">
            ${invitations.map(inv => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; border: 1px solid var(--border-light); border-radius: 6px; margin-bottom: 0.5rem;">
                    <div>
                        <div style="font-weight: 500;">${escapeHtml(inv.email)}</div>
                        <div style="font-size: 0.875rem; color: var(--text-secondary);">
                            Роль: ${getRoleLabel(inv.role)} • Статус: ${getInvitationStatusLabel(inv.status)}
                        </div>
                    </div>
                    ${isOwner && inv.status === 'sent' ? `
                        <button class="btn btn-danger btn-sm" onclick="revokeInvitation(${inv.id})" style="padding: 0.25rem 0.75rem;">
                            Отозвать
                        </button>
                    ` : ''}
                </div>
            `).join('')}
        </div>
    `;
}

function displayInvitations(invitations) {
    const container = document.getElementById('invitationsList');
    if (container) {
        container.innerHTML = renderInvitationsList(invitations);
    }
}

function getRoleLabel(role) {
    const labels = {
        'owner': 'Владелец',
        'editor': 'Редактор',
        'viewer': 'Наблюдатель'
    };
    return labels[role] || role;
}

function getInvitationStatusLabel(status) {
    const labels = {
        'sent': 'Отправлено',
        'accepted': 'Принято',
        'revoked': 'Отозвано',
        'failed': 'Ошибка'
    };
    return labels[status] || status;
}

function saveOrganizationName() {
    const nameInput = document.getElementById('orgNameInput');
    const saveBtn = document.getElementById('saveOrgNameBtn');
    
    if (!nameInput || !currentOrganization) return;
    
    const newName = nameInput.value.trim();
    if (!newName) {
        showMessage('Название организации не может быть пустым', 'error');
        return;
    }
    
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Сохранение...';
    
    fetch(`/api/organizations/${currentOrganization.id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: newName })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Название организации успешно обновлено', 'success');
            currentOrganization.name = newName;
            loadOrganizationDetails(currentOrganization.id);
        } else {
            showMessage(data.error || 'Не удалось обновить название организации', 'error');
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fa-solid fa-save"></i> Сохранить';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Ошибка при обновлении названия организации', 'error');
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fa-solid fa-save"></i> Сохранить';
    });
}

function showInviteMemberModal() {
    const modal = document.getElementById('inviteMemberModal');
    if (modal) {
        modal.classList.add('active');
        document.body.classList.add('modal-open');
        // Reset form
        const form = document.getElementById('inviteMemberForm');
        if (form) {
            form.reset();
        }
        // Focus on email input
        const emailInput = document.getElementById('inviteEmail');
        if (emailInput) {
            setTimeout(() => emailInput.focus(), 100);
        }
    }
}

function closeInviteMemberModal() {
    const modal = document.getElementById('inviteMemberModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.classList.remove('modal-open');
    }
}

function handleInviteMemberSubmit(event) {
    event.preventDefault();
    
    const emailInput = document.getElementById('inviteEmail');
    const roleSelect = document.getElementById('inviteRole');
    const submitBtn = document.getElementById('inviteMemberSubmitBtn');
    
    if (!emailInput || !roleSelect || !currentOrganization) return;
    
    const email = emailInput.value.trim();
    const role = roleSelect.value;
    
    if (!email) {
        showMessage('Введите email пользователя', 'error');
        return;
    }
    
    if (!role || !['viewer', 'editor'].includes(role)) {
        showMessage('Выберите роль', 'error');
        return;
    }
    
    // Disable submit button
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Отправка...';
    
    inviteMember(email, role);
}

function inviteMember(email, role) {
    const submitBtn = document.getElementById('inviteMemberSubmitBtn');
    
    fetch(`/api/organizations/${currentOrganization.id}/members`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email: email, role: role })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage(`Пользователь ${email} успешно приглашён`, 'success');
            closeInviteMemberModal();
            loadOrganizationDetails(currentOrganization.id);
        } else {
            showMessage(data.error || 'Не удалось пригласить пользователя', 'error');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Отправить приглашение';
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Ошибка при приглашении пользователя', 'error');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Отправить приглашение';
        }
    });
}

function changeMemberRole(userId, newRole) {
    if (!confirm('Изменить роль участника?')) {
        // Reload to reset dropdown
        loadOrganizationDetails(currentOrganization.id);
        return;
    }
    
    fetch(`/api/organizations/${currentOrganization.id}/members/${userId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ role: newRole })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Роль участника успешно изменена', 'success');
            loadOrganizationDetails(currentOrganization.id);
        } else {
            showMessage(data.error || 'Не удалось изменить роль участника', 'error');
            loadOrganizationDetails(currentOrganization.id);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Ошибка при изменении роли участника', 'error');
        loadOrganizationDetails(currentOrganization.id);
    });
}

function removeMember(userId, userName) {
    if (!confirm(`Вы уверены, что хотите удалить участника ${userName} из организации?`)) {
        return;
    }
    
    fetch(`/api/organizations/${currentOrganization.id}/members/${userId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Участник успешно удалён из организации', 'success');
            loadOrganizationDetails(currentOrganization.id);
        } else {
            showMessage(data.error || 'Не удалось удалить участника', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Ошибка при удалении участника', 'error');
    });
}

function revokeInvitation(invitationId) {
    if (!confirm('Отозвать приглашение?')) {
        return;
    }
    
    fetch(`/api/organizations/${currentOrganization.id}/invitations/${invitationId}/revoke`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Приглашение успешно отозвано', 'success');
            loadOrganizationInvitations(currentOrganization.id);
        } else {
            showMessage(data.error || 'Не удалось отозвать приглашение', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('Ошибка при отзыве приглашения', 'error');
    });
}

function showOrganizationError(message) {
    const container = document.getElementById('organizationManagementContent');
    if (container) {
        container.innerHTML = `<div style="color: var(--error-red); padding: 1rem;">${escapeHtml(message)}</div>`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions globally available for onclick handlers
window.handleGoogleConnect = handleGoogleConnect;
window.handleGoogleConnectResponse = handleGoogleConnectResponse;
window.closeGoogleConnectModal = closeGoogleConnectModal;
window.setPassword = setPassword;
window.changePassword = changePassword;
window.checkPasswordStrength = checkPasswordStrength;
window.checkPasswordMatch = checkPasswordMatch;
window.sendConfirmationEmail = sendConfirmationEmail;
window.toggleProviderPreference = toggleProviderPreference;
window.saveOrganizationName = saveOrganizationName;
window.showInviteMemberModal = showInviteMemberModal;
window.closeInviteMemberModal = closeInviteMemberModal;
window.handleInviteMemberSubmit = handleInviteMemberSubmit;
window.changeMemberRole = changeMemberRole;
window.removeMember = removeMember;
window.revokeInvitation = revokeInvitation;

