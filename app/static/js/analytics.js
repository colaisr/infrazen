// Analytics Page JavaScript
// Chart.js integration and interactive features

document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for all elements to be ready
    setTimeout(function() {
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded!');
            return;
        }
        
        // Initialize charts with real data
        loadMainSpendingChart();
        loadServiceAnalysisChart();
        loadProviderBreakdownChart();
        
        // Wait a bit more for provider charts to be rendered
        setTimeout(function() {
            loadIndividualProviderCharts();
        }, 200);
        
        // Initialize interactive features
        initializeProviderToggles();
        initializeTimeRangeSelectors();
        initializeExportButton();
    }, 100);
});

// Load Main Spending Chart with Real Data
function loadMainSpendingChart(days = 30) {
    const ctx = document.getElementById('mainSpendingChart');
    if (!ctx) {
        return;
    }
    
    // Show loading state
    ctx.parentElement.innerHTML = '<div class="analytics-chart-loading"><i class="fa-solid fa-spinner"></i> Загрузка данных...</div>';
    
    // Fetch real data from API
    fetch(`/api/analytics/main-trends?days=${days}`)
        .then(response => {
            return response.json();
        })
        .then(data => {
            if (data.success) {
                initializeMainSpendingChart(data.data);
            } else {
                showChartError(ctx, 'Ошибка загрузки данных: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading main trends:', error);
            showChartError(ctx, 'Ошибка загрузки данных: ' + error.message);
        });
}

// Initialize Main Spending Chart with Data
function initializeMainSpendingChart(chartData) {
    
    // Find the chart container
    const chartContainer = document.querySelector('.analytics-chart-content');
    if (!chartContainer) {
        return;
    }
    
    // Restore canvas
    chartContainer.innerHTML = '<canvas id="mainSpendingChart" width="800" height="400"></canvas>';
    const ctx = document.getElementById('mainSpendingChart');
    if (!ctx) {
        return;
    }
    
    try {
        new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: '#1e40af',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + ' ₽/день';
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Дата'
                    },
                    grid: {
                        color: '#e5e7eb'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Расходы (₽/день)'
                    },
                    grid: {
                        color: '#e5e7eb'
                    },
                    ticks: {
                        callback: function(value) {
                            return value.toFixed(2) + ' ₽';
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
    } catch (error) {
        console.error('Error creating main spending chart:', error);
        showChartError(ctx, 'Ошибка создания графика: ' + error.message);
    }
}

// Initialize Service Analysis Chart with Data
function initializeServiceAnalysisChart(chartData) {
    
    // Find the service analysis chart container
    const serviceChartContainer = document.querySelector('.analytics-secondary-grid .analytics-chart-container:first-child .analytics-chart-content');
    if (!serviceChartContainer) {
        return;
    }
    
    // Restore canvas
    serviceChartContainer.innerHTML = '<canvas id="serviceAnalysisChart" width="400" height="300"></canvas>';
    const ctx = document.getElementById('serviceAnalysisChart');
    if (!ctx) {
        return;
    }
    
    // Chart.js data is already formatted, use it directly
    
    new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    callbacks: {
                        label: function(context) {
                            return context.parsed.x + ' ₽/день';
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Расходы (₽/день)'
                    },
                    grid: {
                        color: '#e5e7eb'
                    }
                },
                y: {
                    display: true,
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Service Analysis Chart (Bar Chart) - Legacy function
function initializeServiceAnalysisChartLegacy() {
    const ctx = document.getElementById('serviceAnalysisChart');
    if (!ctx) return;
    
    const chartData = {
        labels: ['Cloud Servers', 'VPS', 'Object Storage', 'Block Storage', 'Load Balancer'],
        datasets: [{
            label: 'Расходы (₽/день)',
            data: [6965, 3517, 1040, 669, 661],
            backgroundColor: [
                '#1e40af',
                '#10b981',
                '#f59e0b',
                '#ef4444',
                '#06b6d4'
            ],
            borderColor: [
                '#1e40af',
                '#10b981',
                '#f59e0b',
                '#ef4444',
                '#06b6d4'
            ],
            borderWidth: 1
        }]
    };
    
    new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    callbacks: {
                        label: function(context) {
                            return context.parsed.x + ' ₽/день';
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Расходы (₽/день)'
                    },
                    grid: {
                        color: '#e5e7eb'
                    }
                },
                y: {
                    display: true,
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Provider Breakdown Chart (Pie Chart)
function initializeProviderBreakdownChart(chartData) {
    
    // Find the provider breakdown chart container by ID
    const ctx = document.getElementById('providerBreakdownChart');
    if (!ctx) {
        console.error('Provider breakdown chart canvas not found');
        return;
    }
    
    // Get the parent container to restore canvas if needed
    const container = ctx.parentElement;
    if (!container) {
        console.error('Provider breakdown chart container not found');
        return;
    }
    
    new Chart(ctx, {
        type: 'doughnut',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return context.label + ': ' + value + ' ₽/день (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
}

// Provider Trend Chart (Line Chart)
function initializeProviderTrendChart() {
    const ctx = document.getElementById('providerTrendChart');
    if (!ctx) return;
    
    const chartData = {
        labels: ['2025-10-10', '2025-10-11', '2025-10-12', '2025-10-13', '2025-10-14', '2025-10-15', '2025-10-16'],
        datasets: [{
            label: 'Beget',
            data: [45.2, 47.8, 46.1, 48.5, 49.2, 48.9, 48.14],
            borderColor: '#1e40af',
            backgroundColor: 'rgba(30, 64, 175, 0.1)',
            tension: 0.4,
            fill: false
        }]
    };
    
    new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white'
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Дата'
                    },
                    grid: {
                        color: '#e5e7eb'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Расходы (₽/день)'
                    },
                    grid: {
                        color: '#e5e7eb'
                    }
                }
            }
        }
    });
}

// Provider Toggle Controls
function initializeProviderToggles() {
    // Provider toggle buttons removed from main chart
    // Main chart now shows only aggregated spending from complete syncs
}

// Time Range Selectors
function initializeTimeRangeSelectors() {
    // Main chart time range selector
    const mainTimeSelector = document.querySelector('.analytics-main-chart-section .analytics-time-selector');
    if (mainTimeSelector) {
        mainTimeSelector.addEventListener('change', function() {
            const days = parseInt(this.value);
            if (days && days !== 'custom') {
                loadMainSpendingChart(days);
            }
        });
    }
    
    // Individual provider chart time range selectors
    const providerTimeSelectors = document.querySelectorAll('.analytics-provider-chart .analytics-time-selector');
    providerTimeSelectors.forEach(selector => {
        selector.addEventListener('change', function() {
            const days = parseInt(this.value);
            const providerId = this.dataset.provider;
            
            if (days && providerId && days !== 'custom') {
                // Reload specific provider chart with new time range
                const canvas = document.getElementById(`providerTrendChart${providerId}`);
                if (canvas) {
                    const container = canvas.parentElement;
                    if (container) {
                        container.innerHTML = '<div class="analytics-chart-loading"><i class="fa-solid fa-spinner"></i> Загрузка данных...</div>';
                        
                        fetch(`/api/analytics/provider-trends/${providerId}?days=${days}`)
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    initializeIndividualProviderChart(container, data.data, providerId);
                                } else {
                                    showChartError(container, 'Ошибка загрузки данных');
                                }
                            })
                            .catch(error => {
                                console.error(`Error reloading provider ${providerId} chart:`, error);
                                showChartError(container, 'Ошибка загрузки данных');
                            });
                    }
                }
            }
        });
    });
}

// Export Button
function initializeExportButton() {
    const exportBtn = document.querySelector('.analytics-export-btn');
    
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            // TODO: Implement export functionality
            alert('Функция экспорта будет реализована в следующей версии');
        });
    }
}


// Load Service Analysis Chart with Real Data
function loadServiceAnalysisChart() {
    const ctx = document.getElementById('serviceAnalysisChart');
    if (!ctx) {
        return;
    }
    
    
    // Show loading state
    ctx.parentElement.innerHTML = '<div class="analytics-chart-loading"><i class="fa-solid fa-spinner"></i> Загрузка данных...</div>';
    
    // Fetch real data from API
    fetch('/api/analytics/service-breakdown')
        .then(response => {
            return response.json();
        })
        .then(data => {
            if (data.success) {
                initializeServiceAnalysisChart(data.data);
            } else {
                showChartError(ctx, 'Ошибка загрузки данных: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading service breakdown:', error);
            showChartError(ctx, 'Ошибка загрузки данных: ' + error.message);
        });
}

// Load Provider Breakdown Chart with Real Data
function loadProviderBreakdownChart() {
    const ctx = document.getElementById('providerBreakdownChart');
    if (!ctx) {
        console.error('Provider breakdown chart canvas not found');
        return;
    }
    
    // Show loading state
    const container = ctx.parentElement;
    if (container) {
        container.innerHTML = '<div class="analytics-chart-loading"><i class="fa-solid fa-spinner"></i> Загрузка данных...</div>';
    }
    
    // Fetch real data from API
    fetch('/api/analytics/provider-breakdown')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Restore canvas before initializing chart
                if (container) {
                    container.innerHTML = '<canvas id="providerBreakdownChart" width="400" height="300"></canvas>';
                }
                initializeProviderBreakdownChart(data.data);
            } else {
                showChartError(container, 'Ошибка загрузки данных: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading provider breakdown:', error);
            showChartError(container, 'Ошибка загрузки данных');
        });
}

// Load Provider Trend Chart with Real Data
// Load Individual Provider Charts
function loadIndividualProviderCharts() {
    
    // Find all provider chart canvases
    const providerCharts = document.querySelectorAll('[id^="providerTrendChart"]');
    
    if (providerCharts.length === 0) {
        // Check if the provider grid exists
        const providerGrid = document.querySelector('.analytics-provider-charts-grid');
        if (providerGrid) {
            // Provider grid exists but no charts found. Providers may not be loaded.
        } else {
            // Provider grid not found. Template may not be rendering correctly.
        }
        return;
    }
    
    providerCharts.forEach(canvas => {
        const providerId = canvas.id.replace('providerTrendChart', '');
        
        // Store container reference before replacing canvas
        const container = canvas.parentElement;
        if (!container) {
            console.error(`Container not found for provider ${providerId}`);
            return;
        }
        
        // Show loading state
        container.innerHTML = '<div class="analytics-chart-loading"><i class="fa-solid fa-spinner"></i> Загрузка данных...</div>';
        
        // Fetch real data from API for this specific provider
        fetch(`/api/analytics/provider-trends/${providerId}?days=30`)
            .then(response => {
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    initializeIndividualProviderChart(container, data.data, providerId);
                } else {
                    showChartError(container, 'Ошибка загрузки данных: ' + data.error);
                }
            })
            .catch(error => {
                console.error(`Error loading provider ${providerId} trends:`, error);
                showChartError(container, 'Ошибка загрузки данных');
            });
    });
}

// Initialize Individual Provider Chart
function initializeIndividualProviderChart(container, chartData, providerId) {
    
    if (!container) {
        console.error(`Container not found for provider ${providerId}`);
        return;
    }
    
    // Restore canvas element
    container.innerHTML = `<canvas id="providerTrendChart${providerId}" width="400" height="300"></canvas>`;
    const newCanvas = document.getElementById(`providerTrendChart${providerId}`);
    
    if (!newCanvas) {
        console.error(`Canvas not found for provider ${providerId}`);
        showChartError(container, 'Ошибка создания canvas');
        return;
    }
    
    try {
        const chart = new Chart(newCanvas, {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Расходы (₽/день)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Дата'
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error(`Error initializing chart for provider ${providerId}:`, error);
        showChartError(container, 'Ошибка инициализации графика');
    }
}

// Show Chart Error
function showChartError(originalCtx, message) {
    if (!originalCtx) {
        console.error('Cannot show chart error: invalid context', originalCtx);
        return;
    }
    
    // Handle both canvas elements and containers
    const container = originalCtx.parentElement || originalCtx;
    if (!container) {
        console.error('Cannot show chart error: no container found');
        return;
    }
    
    container.innerHTML = `
        <div class="analytics-chart-error">
            <i class="fa-solid fa-exclamation-triangle"></i>
            <p>${message}</p>
        </div>
    `;
}

// Utility functions
function formatCurrency(value) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 2
    }).format(value);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('ru-RU', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(new Date(date));
}
