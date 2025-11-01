/**
 * InfraZen - Resources Page JavaScript
 * Handles resource display, charts, and CSV export
 */

// ============================================================================
// Toggle Functions
// ============================================================================

function toggleProviderSection(providerId) {
    const content = document.getElementById(`provider-content-${providerId}`);
    const chevron = document.getElementById(`provider-chevron-${providerId}`);
    
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        chevron.classList.add('rotated');
    } else {
        content.style.display = 'none';
        chevron.classList.remove('rotated');
    }
}

function toggleUsageSection(resourceId) {
    const content = document.getElementById(`usage-info-${resourceId}`);
    const chevron = document.getElementById(`usage-chevron-${resourceId}`);
    
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        chevron.classList.add('rotated');
        
        // Initialize charts when usage section is opened
        initializeCharts(resourceId);
    } else {
        content.style.display = 'none';
        chevron.classList.remove('rotated');
    }
}

function toggleCostBreakdown(resourceId) {
    const content = document.getElementById(`cost-breakdown-${resourceId}`);
    const chevron = document.getElementById(`cost-chevron-${resourceId}`);
    
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        chevron.classList.add('rotated');
    } else {
        content.style.display = 'none';
        chevron.classList.remove('rotated');
    }
}

function toggleCSIVolumes(resourceId) {
    const content = document.getElementById(`csi-volumes-${resourceId}`);
    const chevron = document.getElementById(`csi-chevron-${resourceId}`);
    
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        chevron.style.transform = 'rotate(180deg)';
    } else {
        content.style.display = 'none';
        chevron.style.transform = 'rotate(0deg)';
    }
}

function toggleWorkerVMs(resourceId) {
    const content = document.getElementById(`worker-vms-${resourceId}`);
    const chevron = document.getElementById(`worker-chevron-${resourceId}`);
    
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        chevron.style.transform = 'rotate(180deg)';
    } else {
        content.style.display = 'none';
        chevron.style.transform = 'rotate(0deg)';
    }
}

// ============================================================================
// Chart Initialization
// ============================================================================

function initializeCharts(resourceId) {
    // Wait for Chart.js to load
    if (typeof Chart === 'undefined') {
        console.log('Chart.js not loaded yet, retrying in 100ms...');
        setTimeout(() => initializeCharts(resourceId), 100);
        return;
    }
    
    // Initialize CPU chart if canvas exists
    const cpuCanvas = document.getElementById(`cpu-chart-${resourceId}`);
    if (cpuCanvas && !cpuCanvas.chart) {
        createCpuChart(cpuCanvas, resourceId);
    }
    
    // Initialize Memory chart if canvas exists
    const memoryCanvas = document.getElementById(`memory-chart-${resourceId}`);
    if (memoryCanvas && !memoryCanvas.chart) {
        createMemoryChart(memoryCanvas, resourceId);
    }
}

function createCpuChart(canvas, resourceId) {
    const ctx = canvas.getContext('2d');
    
    // Get real CPU data from the resource tags
    let labels = [];
    let cpuData = [];
    
    // Try to get real data from hidden inputs
    const cpuRawDataInput = document.getElementById(`cpu-raw-data-${resourceId}`);
    if (cpuRawDataInput) {
        try {
            const rawData = JSON.parse(cpuRawDataInput.value);
            if (rawData.dates && rawData.values) {
                // Use real data
                labels = rawData.dates.map(date => {
                    const d = new Date(date);
                    return d.toLocaleDateString('en-GB', { 
                        day: '2-digit', 
                        month: '2-digit' 
                    });
                });
                cpuData = rawData.values;
            }
        } catch (e) {
            console.log('Could not parse CPU raw data:', e);
        }
    }
    
    // Fallback to sample data if no real data available
    if (labels.length === 0) {
        const now = new Date();
        for (let i = 30; i >= 0; i--) {
            const time = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
            labels.push(time.toLocaleDateString('en-GB', { 
                day: '2-digit', 
                month: '2-digit' 
            }));
            
            // Generate realistic CPU data (0-2% range for low usage)
            const baseCpu = 0.5;
            const variation = (Math.random() - 0.5) * 1;
            cpuData.push(Math.max(0, Math.min(5, baseCpu + variation)));
        }
    }
    
    canvas.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'CPU Usage',
                data: cpuData,
                borderColor: '#1E40AF',
                backgroundColor: 'rgba(30, 64, 175, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: '#1E40AF',
                pointBorderColor: '#1E40AF'
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
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        color: '#E5E7EB'
                    }
                },
                x: {
                    grid: {
                        color: '#E5E7EB'
                    }
                }
            },
            elements: {
                point: {
                    radius: 3
                }
            }
        }
    });
}

function createMemoryChart(canvas, resourceId) {
    const ctx = canvas.getContext('2d');
    
    // Get real memory data from the resource tags
    let labels = [];
    let memoryData = [];
    
    // Try to get real data from hidden inputs
    const memoryRawDataInput = document.getElementById(`memory-raw-data-${resourceId}`);
    if (memoryRawDataInput) {
        try {
            const rawData = JSON.parse(memoryRawDataInput.value);
            if (rawData.dates && rawData.values) {
                // Use real data
                labels = rawData.dates.map(date => {
                    const d = new Date(date);
                    return d.toLocaleDateString('en-GB', { 
                        day: '2-digit', 
                        month: '2-digit' 
                    });
                });
                // Convert memory values from MB to GB for display
                memoryData = rawData.values.map(mb => mb / 1024);
            }
        } catch (e) {
            console.log('Could not parse memory raw data:', e);
        }
    }
    
    // Fallback to sample data if no real data available
    if (labels.length === 0) {
        const now = new Date();
        for (let i = 30; i >= 0; i--) {
            const time = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
            labels.push(time.toLocaleDateString('en-GB', { 
                day: '2-digit', 
                month: '2-digit' 
            }));
            
            // Generate realistic memory data (0.9-1.0 GB range)
            const baseMemory = 0.95;
            const memVariation = (Math.random() - 0.5) * 0.1;
            memoryData.push(Math.max(0.8, Math.min(1.2, baseMemory + memVariation)));
        }
    }
    
    // Get total RAM from VM metadata to set Y-axis maximum
    let maxMemory = Math.max.apply(null, memoryData) * 1.2; // Fallback to auto-scale
    const totalRamInput = document.getElementById(`total-ram-mb-${resourceId}`);
    if (totalRamInput && totalRamInput.value) {
        const totalRamMB = parseFloat(totalRamInput.value);
        if (totalRamMB > 0) {
            // Convert MB to GB and use as Y-axis maximum
            maxMemory = totalRamMB / 1024;
        }
    }
    
    canvas.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Memory Usage',
                data: memoryData,
                borderColor: '#1E40AF',
                backgroundColor: 'rgba(30, 64, 175, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: '#1E40AF',
                pointBorderColor: '#1E40AF'
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
                    max: maxMemory,
                    ticks: {
                        callback: function(value) {
                            return value.toFixed(1) + ' GB';
                        }
                    },
                    grid: {
                        color: '#E5E7EB'
                    }
                },
                x: {
                    grid: {
                        color: '#E5E7EB'
                    }
                }
            },
            elements: {
                point: {
                    radius: 3
                }
            }
        }
    });
}

// ============================================================================
// CSV Export
// ============================================================================

function exportResourcesToCSV() {
    // Check if SheetJS (XLSX) library is available
    if (typeof XLSX === 'undefined') {
        console.error('SheetJS library not loaded, falling back to CSV export');
        exportResourcesToCSVFallback();
        return;
    }
    
    // Get all provider sections
    const providerSections = document.querySelectorAll('.provider-section');
    
    // Get summary statistics
    const summaryStats = document.querySelector('.summary-stats');
    const totalResources = summaryStats?.querySelector('.stat-value')?.textContent || '0';
    const totalCost = summaryStats?.querySelectorAll('.stat-value')[1]?.textContent || '0 ₽/день';
    
    // Create workbook
    const wb = XLSX.utils.book_new();
    
    // Create summary sheet
    const summaryData = [
        ['ЭКСПОРТ РЕСУРСОВ - InfraZen FinOps Platform'],
        ['Дата экспорта:', new Date().toLocaleDateString('ru-RU')],
        [],
        ['ОБЩАЯ СТАТИСТИКА:'],
        ['Всего ресурсов:', totalResources],
        ['Общая стоимость:', totalCost],
        [],
        ['ДЕТАЛЬНЫЕ ДАННЫЕ:']
    ];
    
    const ws_summary = XLSX.utils.aoa_to_sheet(summaryData);
    
    // Set column widths for summary
    ws_summary['!cols'] = [
        { wch: 30 },
        { wch: 20 }
    ];
    
    // Create resources data array
    const resourcesData = [
        ['Провайдер', 'Ресурс', 'Тип', 'Статус', 'External IP', 'Регион', 'Стоимость день (₽)', 'Стоимость месяц (₽)']
    ];
    
    // Process each provider section
    providerSections.forEach(section => {
        const providerName = section.querySelector('.provider-name').textContent;
        const resourceCards = section.querySelectorAll('.resource-card');
        
        if (resourceCards.length === 0) {
            resourcesData.push([providerName, 'Нет ресурсов', '', '', '', '', '', '']);
        } else {
            resourceCards.forEach(card => {
                const resourceName = card.querySelector('.resource-name').textContent;
                const resourceType = card.querySelector('.resource-type').textContent;
                const status = card.querySelector('.status-badge').textContent.trim();
                const externalIp = card.querySelector('.detail-row:nth-child(1) .detail-value').textContent;
                const region = card.querySelector('.detail-row:nth-child(2) .detail-value').textContent;
                const costMonthly = card.querySelector('.detail-row:nth-child(3) .detail-value').textContent;
                const costDaily = card.querySelector('.detail-row:nth-child(4) .detail-value').textContent;
                
                // Extract numeric values from cost strings
                const dailyNumeric = parseFloat(costDaily.replace(/[^\d.,]/g, '').replace(',', '.')) || 0;
                const monthlyNumeric = parseFloat(costMonthly.replace(/[^\d.,]/g, '').replace(',', '.')) || 0;
                
                resourcesData.push([
                    providerName,
                    resourceName,
                    resourceType,
                    status,
                    externalIp,
                    region,
                    dailyNumeric,
                    monthlyNumeric
                ]);
            });
        }
    });
    
    // Create resources worksheet
    const ws_resources = XLSX.utils.aoa_to_sheet(resourcesData);
    
    // Set column widths
    ws_resources['!cols'] = [
        { wch: 15 }, // Провайдер
        { wch: 35 }, // Ресурс
        { wch: 20 }, // Тип
        { wch: 12 }, // Статус
        { wch: 15 }, // External IP
        { wch: 20 }, // Регион
        { wch: 18 }, // Стоимость день
        { wch: 18 }  // Стоимость месяц
    ];
    
    // Add both sheets to workbook
    XLSX.utils.book_append_sheet(wb, ws_summary, 'Сводка');
    XLSX.utils.book_append_sheet(wb, ws_resources, 'Ресурсы');
    
    // Generate Excel file and download
    const fileName = `resources_${new Date().toISOString().split('T')[0]}.xlsx`;
    XLSX.writeFile(wb, fileName);
}

// Fallback CSV export if XLSX library not available
function exportResourcesToCSVFallback() {
    const providerSections = document.querySelectorAll('.provider-section');
    let csvContent = '\uFEFF'; // UTF-8 BOM for proper encoding
    
    csvContent += 'ЭКСПОРТ РЕСУРСОВ - InfraZen FinOps Platform\n';
    csvContent += 'Дата экспорта: ' + new Date().toLocaleDateString('ru-RU') + '\n';
    csvContent += '\n';
    
    const summaryStats = document.querySelector('.summary-stats');
    if (summaryStats) {
        const totalResources = summaryStats.querySelector('.stat-value')?.textContent || '0';
        const totalCost = summaryStats.querySelectorAll('.stat-value')[1]?.textContent || '0 ₽/день';
        csvContent += 'ОБЩАЯ СТАТИСТИКА:\n';
        csvContent += 'Всего ресурсов: ' + totalResources + '\n';
        csvContent += 'Общая стоимость: ' + totalCost + '\n';
        csvContent += '\n';
    }
    
    csvContent += 'ДЕТАЛЬНЫЕ ДАННЫЕ:\n';
    csvContent += 'Провайдер,Ресурс,Тип,Статус,External IP,Регион,Стоимость (₽/день)\n';
    
    providerSections.forEach(section => {
        const providerName = section.querySelector('.provider-name').textContent;
        const resourceCards = section.querySelectorAll('.resource-card');
        
        if (resourceCards.length === 0) {
            csvContent += `"${providerName}","Нет ресурсов","","","","",""\n`;
        } else {
            resourceCards.forEach(card => {
                const resourceName = card.querySelector('.resource-name').textContent;
                const resourceType = card.querySelector('.resource-type').textContent;
                const status = card.querySelector('.status-badge').textContent.trim();
                const externalIp = card.querySelector('.detail-row:nth-child(1) .detail-value').textContent;
                const region = card.querySelector('.detail-row:nth-child(2) .detail-value').textContent;
                const cost = card.querySelector('.detail-row:nth-child(3) .detail-value').textContent;
                
                csvContent += `"${providerName}","${resourceName}","${resourceType}","${status}","${externalIp}","${region}","${cost}"\n`;
            });
        }
    });
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `resources_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Make functions globally available for onclick handlers
window.toggleProviderSection = toggleProviderSection;
window.toggleUsageSection = toggleUsageSection;
window.toggleCostBreakdown = toggleCostBreakdown;
window.toggleCSIVolumes = toggleCSIVolumes;
window.toggleWorkerVMs = toggleWorkerVMs;
window.exportResourcesToCSV = exportResourcesToCSV;

