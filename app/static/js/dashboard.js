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
});

