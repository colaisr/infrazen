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
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    loadUserDetails();
    loadProviderPreferences();
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

