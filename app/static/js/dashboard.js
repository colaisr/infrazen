/**
 * InfraZen - Dashboard Page JavaScript
 * Handles dashboard-specific functionality
 */

// ============================================================================
// Expense Dynamics Chart
// ============================================================================

let expenseChart = null;

/**
 * Initialize the expense dynamics chart
 */
function initExpenseDynamicsChart() {
    const ctx = document.getElementById('expenseDynamicsChart');
    if (!ctx) return;
    
    // Get trend data from data attribute
    const chartContainer = ctx.closest('.chart-container');
    const trendData = JSON.parse(chartContainer.dataset.trendData || '[]');
    
    const labels = trendData.map(item => item.date);
    const costs = trendData.map(item => item.cost);
    
    expenseChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Месячные расходы (₽)',
                data: costs,
                borderColor: '#1e40af',
                backgroundColor: 'rgba(30, 64, 175, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₽' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize time range filter buttons
 */
function initTimeRangeFilters() {
    const filterButtons = document.querySelectorAll('.filter-controls .filter-pill');
    
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            filterButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Get the selected days
            const days = parseInt(this.dataset.days);
            
            // Reload chart with new time range
            loadExpenseDynamicsData(days);
        });
    });
}

/**
 * Load expense dynamics data for a specific time range
 * @param {number} days - Number of days to load
 */
function loadExpenseDynamicsData(days) {
    // Show loading state
    if (expenseChart) {
        expenseChart.destroy();
    }
    
    const ctx = document.getElementById('expenseDynamicsChart');
    if (ctx && ctx.parentElement) {
        ctx.parentElement.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 200px;"><i class="fa-solid fa-spinner fa-spin"></i> Загрузка данных...</div>';
    }
    
    // Fetch new data based on time range
    fetch(`/api/analytics/main-trends?days=${days}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Restore canvas
                const container = document.querySelector('.chart-container');
                if (container) {
                    container.innerHTML = '<canvas id="expenseDynamicsChart" width="400" height="200"></canvas>';
                }
                
                // Create new chart with fetched data
                const newCtx = document.getElementById('expenseDynamicsChart');
                expenseChart = new Chart(newCtx, {
                    type: 'line',
                    data: data.data,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        return '₽' + value.toLocaleString();
                                    }
                                }
                            }
                        }
                    }
                });
            } else {
                console.error('Failed to load expense dynamics data:', data.error);
            }
        })
        .catch(error => {
            console.error('Error loading expense dynamics data:', error);
        });
}

// ============================================================================
// Initialize Dashboard
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Load Chart.js if not already loaded
    if (typeof Chart === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        script.onload = function() {
            initExpenseDynamicsChart();
            initTimeRangeFilters();
        };
        document.head.appendChild(script);
    } else {
        initExpenseDynamicsChart();
        initTimeRangeFilters();
    }
    loadDashboardRecommendations();
    loadDashboardResources();
});

// ==========================================================================
// Dashboard Recommendations (Top 5 pending)
// ==========================================================================

function renderDashboardRecs(items) {
    const container = document.getElementById('dashboard-recs');
    if (!container) return;
    if (!items || items.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon"><i class="fa-solid fa-lightbulb"></i></div><div class="empty-state-title">Рекомендации не найдены</div><div class="empty-state-text">Все ваши ресурсы оптимально настроены</div></div>';
        return;
    }

    const rows = items.map(rec => {
        const sevColor = {critical:'#ef4444', high:'#f59e0b', medium:'#10b981', low:'#3b82f6', info:'#6b7280'}[rec.severity] || '#6b7280';
        const savings = new Intl.NumberFormat('ru-RU').format(Math.round(rec.estimated_monthly_savings || rec.potential_savings || 0));
        const provider = rec.provider_code ? `<span class="chip">${rec.provider_code}</span>` : '';
        const resource = rec.resource_name ? `<span class="chip">${rec.resource_name}</span>` : '';
        return `
            <div class="rec-mini-row">
                <span class="sev-dot" style="background:${sevColor}"></span>
                <a class="rec-mini-title" href="/recommendations" title="Открыть рекомендации">${rec.title || 'Рекомендация'}</a>
                <span class="rec-mini-context">${provider} ${resource}</span>
                <span class="rec-mini-savings"><span class="savings-label">экономия</span> ₽${savings}/мес</span>
            </div>
        `;
    }).join('');

    const footer = `<div class="rec-mini-footer"><a href="/recommendations?status=pending" class="link-button">Показать все</a></div>`;
    container.innerHTML = rows + footer;
}

function loadDashboardRecommendations() {
    const container = document.getElementById('dashboard-recs');
    if (!container) return;
    fetch('/api/recommendations?status=pending&page=1&page_size=5&order_by=-estimated_monthly_savings')
        .then(r => r.json())
        .then(data => {
            renderDashboardRecs((data && data.items) || []);
        })
        .catch(() => {
            renderDashboardRecs([]);
        });
}

// ==========================================================================
// Dashboard Resources (Top 10 from last sync)
// ==========================================================================

// Store all resources globally for filtering
let allDashboardResources = [];
let totalDashboardResources = 0;

function loadDashboardResources() {
    const container = document.getElementById('dashboard-resources-table');
    const countEl = document.getElementById('resource-count');
    if (!container) return;
    
    fetch('/api/dashboard/resources')
        .then(r => r.json())
        .then(data => {
            if (data.success && data.resources && data.resources.length > 0) {
                allDashboardResources = data.resources;
                totalDashboardResources = data.total || data.resources.length;
                populateDashboardResourceFilters(data.resources);
                renderDashboardResources(data.resources, data.total || data.resources.length);
                setupDashboardResourceFilters();
            } else {
                container.innerHTML = '<div class="empty-state"><div class="empty-state-icon"><i class="fa-solid fa-server"></i></div><div class="empty-state-title">Нет ресурсов</div><div class="empty-state-text">Подключите облачных провайдеров для отображения ресурсов</div></div>';
                if (countEl) countEl.textContent = '0 из 0 ресурсов';
            }
        })
        .catch(() => {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon"><i class="fa-solid fa-server"></i></div><div class="empty-state-title">Нет ресурсов</div><div class="empty-state-text">Подключите облачных провайдеров для отображения ресурсов</div></div>';
            if (countEl) countEl.textContent = '0 из 0 ресурсов';
        });
}

function populateDashboardResourceFilters(resources) {
    // Populate provider dropdown
    const providerSelect = document.getElementById('dashboard-resource-provider');
    const providers = [...new Set(resources.map(r => r.provider_name).filter(Boolean))];
    providers.forEach(provider => {
        const option = document.createElement('option');
        option.value = provider;
        option.textContent = provider;
        providerSelect.appendChild(option);
    });
    
    // Populate type dropdown
    const typeSelect = document.getElementById('dashboard-resource-type');
    const types = [...new Set(resources.map(r => r.resource_type).filter(Boolean))];
    types.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        typeSelect.appendChild(option);
    });
    
    // Populate status dropdown
    const statusSelect = document.getElementById('dashboard-resource-status');
    const statuses = [...new Set(resources.map(r => r.status).filter(Boolean))];
    statuses.forEach(status => {
        const option = document.createElement('option');
        option.value = status;
        option.textContent = status;
        statusSelect.appendChild(option);
    });
}

function setupDashboardResourceFilters() {
    const searchInput = document.getElementById('dashboard-resource-search');
    const providerSelect = document.getElementById('dashboard-resource-provider');
    const typeSelect = document.getElementById('dashboard-resource-type');
    const statusSelect = document.getElementById('dashboard-resource-status');
    
    const applyFilters = () => {
        const searchTerm = (searchInput?.value || '').toLowerCase();
        const selectedProvider = providerSelect?.value || '';
        const selectedType = typeSelect?.value || '';
        const selectedStatus = statusSelect?.value || '';
        
        let filtered = allDashboardResources;
        
        // Search across all columns (case-insensitive)
        if (searchTerm) {
            filtered = filtered.filter(r => {
                const searchableText = [
                    r.resource_name,
                    r.name,
                    r.provider_name,
                    r.provider_type,
                    r.resource_type,
                    r.type,
                    r.region,
                    r.status
                ].filter(Boolean).join(' ').toLowerCase();
                
                return searchableText.includes(searchTerm);
            });
        }
        
        // Filter by provider
        if (selectedProvider) {
            filtered = filtered.filter(r => r.provider_name === selectedProvider);
        }
        
        // Filter by type
        if (selectedType) {
            filtered = filtered.filter(r => r.resource_type === selectedType);
        }
        
        // Filter by status
        if (selectedStatus) {
            filtered = filtered.filter(r => r.status === selectedStatus);
        }
        
        renderDashboardResources(filtered, totalDashboardResources);
    };
    
    if (searchInput) searchInput.addEventListener('input', applyFilters);
    if (providerSelect) providerSelect.addEventListener('change', applyFilters);
    if (typeSelect) typeSelect.addEventListener('change', applyFilters);
    if (statusSelect) statusSelect.addEventListener('change', applyFilters);
}

function renderDashboardResources(resources, total) {
    const container = document.getElementById('dashboard-resources-table');
    const countEl = document.getElementById('resource-count');
    if (!container) return;
    
    // Show top 10 from the filtered list
    const displayResources = resources.slice(0, 10);
    
    if (countEl) countEl.textContent = `${displayResources.length} из ${total} ресурсов`;
    
    const header = `
        <div class="resource-table-header">
            <span>Ресурс</span>
            <span>Провайдер</span>
            <span>Тип</span>
            <span>Регион</span>
            <span>Статус</span>
            <span>Стоимость</span>
        </div>
    `;
    
    const rows = displayResources.map(r => {
        const statusClass = r.status === 'active' || r.status === 'running' ? 'status-active' : 'status-stopped';
        const monthlyCost = ((r.daily_cost || 0) * 30).toFixed(0);
        return `
            <div class="resource-row">
                <span title="${r.resource_name || r.name}">${r.resource_name || r.name || '—'}</span>
                <span>${r.provider_name || r.provider_type || '—'}</span>
                <span>${r.resource_type || r.type || '—'}</span>
                <span>${r.region || '—'}</span>
                <span class="${statusClass}">${r.status || '—'}</span>
                <span>₽${new Intl.NumberFormat('ru-RU').format(monthlyCost)}/мес</span>
            </div>
        `;
    }).join('');
    
    const footer = `<div class="resource-table-footer"><a href="/resources" class="link-button">Открыть все ресурсы</a></div>`;
    
    container.innerHTML = header + rows + footer;
}

