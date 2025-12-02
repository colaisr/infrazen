/**
 * Organization Switcher JavaScript
 * Handles organization switching and management UI
 */

let organizations = [];
let currentOrganizationId = null;

/**
 * Initialize organization switcher on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    loadOrganizations();
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(event) {
        const dropdown = document.getElementById('orgSwitcherMenu');
        const button = document.getElementById('orgSwitcherButton');
        
        if (dropdown && button && !dropdown.contains(event.target) && !button.contains(event.target)) {
            dropdown.style.display = 'none';
        }
    });
});

/**
 * Load user's organizations from API
 */
async function loadOrganizations() {
    try {
        const response = await fetch('/api/organizations');
        const data = await response.json();
        
        if (data.success) {
            organizations = data.organizations || [];
            currentOrganizationId = data.current_organization_id;
            renderOrganizationSwitcher();
        } else {
            console.error('Failed to load organizations:', data.error);
            showError('Не удалось загрузить организации');
        }
    } catch (error) {
        console.error('Error loading organizations:', error);
        showError('Ошибка при загрузке организаций');
    }
}

/**
 * Render organization switcher UI
 */
function renderOrganizationSwitcher() {
    const currentOrg = organizations.find(org => org.id === currentOrganizationId);
    const currentOrgElement = document.getElementById('orgSwitcherCurrent');
    const orgListElement = document.getElementById('orgSwitcherList');
    
    if (!currentOrgElement || !orgListElement) {
        return;
    }
    
    // Update current organization display
    if (currentOrg) {
        currentOrgElement.textContent = currentOrg.name;
        currentOrgElement.setAttribute('data-org-id', currentOrg.id);
    } else {
        currentOrgElement.textContent = 'Выберите организацию';
    }
    
    // Render organization list
    orgListElement.innerHTML = '';
    
    if (organizations.length === 0) {
        orgListElement.innerHTML = '<div class="org-switcher-empty">Нет организаций</div>';
        return;
    }
    
    organizations.forEach(org => {
        const orgItem = document.createElement('div');
        orgItem.className = 'org-switcher-item';
        if (org.id === currentOrganizationId) {
            orgItem.classList.add('active');
        }
        
        const roleBadge = getRoleBadge(org.role);
        const isPersonal = org.is_personal ? '<span class="org-personal-badge">Личная</span>' : '';
        
        orgItem.innerHTML = `
            <div class="org-item-content">
                <div class="org-item-name">${escapeHtml(org.name)}</div>
                <div class="org-item-meta">
                    ${roleBadge}
                    ${isPersonal}
                </div>
            </div>
            ${org.id === currentOrganizationId ? '<i class="fa-solid fa-check org-item-check"></i>' : ''}
        `;
        
        orgItem.addEventListener('click', () => switchOrganization(org.id));
        orgListElement.appendChild(orgItem);
    });
}

/**
 * Get role badge HTML
 */
function getRoleBadge(role) {
    const badges = {
        'owner': '<span class="org-role-badge org-role-owner">Владелец</span>',
        'editor': '<span class="org-role-badge org-role-editor">Редактор</span>',
        'viewer': '<span class="org-role-badge org-role-viewer">Наблюдатель</span>'
    };
    return badges[role] || '';
}

/**
 * Toggle organization dropdown
 */
function toggleOrgDropdown(event) {
    event.stopPropagation();
    const menu = document.getElementById('orgSwitcherMenu');
    if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    }
}

/**
 * Switch to a different organization
 */
async function switchOrganization(orgId) {
    if (orgId === currentOrganizationId) {
        // Already active, just close dropdown
        document.getElementById('orgSwitcherMenu').style.display = 'none';
        return;
    }
    
    try {
        // Show loading state
        const currentOrgElement = document.getElementById('orgSwitcherCurrent');
        if (currentOrgElement) {
            currentOrgElement.textContent = 'Переключение...';
        }
        
        const response = await fetch(`/api/organizations/${orgId}/switch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update current organization ID
            currentOrganizationId = data.current_organization_id || orgId;
            
            // Force full page reload with cache busting to ensure fresh data
            // Use setTimeout to ensure the API response is fully processed
            // Use window.location.reload(true) for hard reload, or navigate to current page with cache bust
            setTimeout(() => {
                // Hard reload to ensure fresh data from server
                const currentUrl = window.location.href.split('?')[0];
                window.location.href = currentUrl + '?org_switched=' + Date.now() + '&_=' + Math.random();
            }, 200);
        } else {
            showError(data.error || 'Не удалось переключить организацию');
            // Restore current org name
            loadOrganizations();
        }
    } catch (error) {
        console.error('Error switching organization:', error);
        showError('Ошибка при переключении организации');
        loadOrganizations();
    }
}


/**
 * Show error message
 */
function showError(message) {
    if (typeof showFlashMessage === 'function') {
        showFlashMessage(message, 'error');
    } else {
        alert(message);
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

