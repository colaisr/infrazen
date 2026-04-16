/**
 * InfraZen - Resources Page JavaScript
 * Handles resource display, charts, and CSV export
 */

// ============================================================================
// Toggle Functions
// ============================================================================

function toggleProviderSection(providerId) {
    try {
        const content = document.getElementById(`provider-content-${providerId}`);
        const chevron = document.getElementById(`provider-chevron-${providerId}`);
        
        if (!content) {
            console.error(`Provider content not found for ID: ${providerId}`);
            return;
        }
        
        if (!chevron) {
            console.error(`Provider chevron not found for ID: ${providerId}`);
            return;
        }
        
        if (content.style.display === 'none' || content.style.display === '') {
            content.style.display = 'block';
            chevron.classList.add('rotated');
        } else {
            content.style.display = 'none';
            chevron.classList.remove('rotated');
        }
    } catch (error) {
        console.error('Error in toggleProviderSection:', error);
    }
}

// Export to window immediately for onclick handlers
window.toggleProviderSection = toggleProviderSection;

/** Match Jinja `{:,.2f}` style for provider header totals */
function formatProviderMoney(n) {
    const x = typeof n === 'number' && !isNaN(n) ? n : 0;
    return x.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Match Jinja `replace('-',' ')|replace('_',' ')|title` for type filter labels */
function formatTypeOptionLabel(typeKey) {
    if (!typeKey) return '';
    return String(typeKey)
        .replace(/[-_]/g, ' ')
        .split(/\s+/)
        .filter(Boolean)
        .map(function (w) {
            return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
        })
        .join(' ');
}

function cardMatchesTenant(card, tenantVal) {
    if (!tenantVal) return true;
    const raw = card.getAttribute('data-tenant') || '';
    if (tenantVal === '__empty__') return raw === '';
    return raw === tenantVal;
}

function cardMatchesEnterprise(card, enterpriseVal) {
    if (!enterpriseVal) return true;
    const raw = (card.getAttribute('data-enterprise-project') || '').trim();
    if (enterpriseVal === '__empty__') return raw === '';
    return raw === enterpriseVal;
}

function cardMatchesType(card, typeVal) {
    if (!typeVal) return true;
    const cardType = (card.getAttribute('data-resource-type') || '').toLowerCase();
    return cardType === typeVal.toLowerCase();
}

/** Match all active filters except those excluded (for rebuilding one axis). */
function cardMatchesFilters(card, f, exclude) {
    exclude = exclude || {};
    if (!exclude.tenant && f.tenant && !cardMatchesTenant(card, f.tenant)) return false;
    if (!exclude.enterprise && f.enterprise && !cardMatchesEnterprise(card, f.enterprise)) return false;
    if (!exclude.type && f.type && !cardMatchesType(card, f.type)) return false;
    return true;
}

function getProviderFilterState(providerId) {
    const tenantSelect = document.getElementById('provider-tenant-filter-' + providerId);
    const enterpriseSelect = document.getElementById('provider-enterprise-filter-' + providerId);
    const typeSelect = document.getElementById('provider-type-filter-' + providerId);
    return {
        tenant: tenantSelect ? tenantSelect.value : '',
        enterprise: enterpriseSelect ? enterpriseSelect.value : '',
        type: typeSelect ? typeSelect.value : ''
    };
}

function selectHasValue(selectEl, val) {
    if (!selectEl) return false;
    for (let i = 0; i < selectEl.options.length; i++) {
        if (selectEl.options[i].value === val) return true;
    }
    return false;
}

function rebuildTenantSelect(providerId, cards, f) {
    const sel = document.getElementById('provider-tenant-filter-' + providerId);
    if (!sel) return;
    const prev = sel.value;
    const set = new Set();
    cards.forEach(function (card) {
        if (!cardMatchesFilters(card, f, { tenant: true })) return;
        set.add(card.getAttribute('data-tenant') || '');
    });
    const hasEmpty = set.has('');
    const values = Array.from(set).filter(function (x) { return x !== ''; }).sort(function (a, b) {
        return a.localeCompare(b, 'ru');
    });
    sel.innerHTML = '';
    const o0 = document.createElement('option');
    o0.value = '';
    o0.textContent = 'Все tenant';
    sel.appendChild(o0);
    if (hasEmpty) {
        const oe = document.createElement('option');
        oe.value = '__empty__';
        oe.textContent = '— (не задан)';
        sel.appendChild(oe);
    }
    values.forEach(function (t) {
        const o = document.createElement('option');
        o.value = t;
        o.textContent = t;
        sel.appendChild(o);
    });
    if (selectHasValue(sel, prev)) sel.value = prev;
    else sel.value = '';
}

function rebuildEnterpriseSelect(providerId, cards, f) {
    const sel = document.getElementById('provider-enterprise-filter-' + providerId);
    if (!sel) return;
    const prev = sel.value;
    const set = new Set();
    cards.forEach(function (card) {
        if (!cardMatchesFilters(card, f, { enterprise: true })) return;
        set.add((card.getAttribute('data-enterprise-project') || '').trim());
    });
    const hasEmpty = set.has('');
    const values = Array.from(set).filter(function (x) { return x !== ''; }).sort(function (a, b) {
        return a.localeCompare(b, 'ru');
    });
    sel.innerHTML = '';
    const o0 = document.createElement('option');
    o0.value = '';
    o0.textContent = 'Все проекты';
    sel.appendChild(o0);
    if (hasEmpty) {
        const oe = document.createElement('option');
        oe.value = '__empty__';
        oe.textContent = '— (не задан)';
        sel.appendChild(oe);
    }
    values.forEach(function (ep) {
        const o = document.createElement('option');
        o.value = ep;
        o.textContent = ep;
        sel.appendChild(o);
    });
    if (selectHasValue(sel, prev)) sel.value = prev;
    else sel.value = '';
}

function rebuildTypeSelect(providerId, cards, f) {
    const sel = document.getElementById('provider-type-filter-' + providerId);
    if (!sel) return;
    const prev = sel.value;
    const set = new Set();
    cards.forEach(function (card) {
        if (!cardMatchesFilters(card, f, { type: true })) return;
        const t = (card.getAttribute('data-resource-type') || '').toLowerCase();
        if (t) set.add(t);
    });
    const typesToShow = Array.from(set).sort();
    sel.innerHTML = '';
    const optAll = document.createElement('option');
    optAll.value = '';
    optAll.textContent = 'Все типы';
    sel.appendChild(optAll);
    typesToShow.forEach(function (t) {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = formatTypeOptionLabel(t);
        sel.appendChild(opt);
    });
    if (selectHasValue(sel, prev)) sel.value = prev;
    else sel.value = '';
}

function syncProviderFilterSelects(providerId) {
    const grid = document.getElementById('provider-grid-' + providerId);
    if (!grid) return;
    const cards = grid.querySelectorAll('.resource-card');
    for (let i = 0; i < 10; i++) {
        const f = getProviderFilterState(providerId);
        rebuildTenantSelect(providerId, cards, f);
        rebuildEnterpriseSelect(providerId, cards, f);
        rebuildTypeSelect(providerId, cards, f);
        const f2 = getProviderFilterState(providerId);
        if (f2.tenant === f.tenant && f2.enterprise === f.enterprise && f2.type === f.type) break;
    }
}

function applyProviderFilters(providerId) {
    const grid = document.getElementById('provider-grid-' + providerId);
    const countEl = document.getElementById('provider-filtered-count-' + providerId);
    const monthlyEl = document.getElementById('provider-summary-monthly-' + providerId);
    const dailyEl = document.getElementById('provider-summary-daily-' + providerId);
    const countSummaryEl = document.getElementById('provider-summary-count-' + providerId);
    const section = document.getElementById('provider-section-' + providerId);
    const tenantSelect = document.getElementById('provider-tenant-filter-' + providerId);
    const enterpriseSelect = document.getElementById('provider-enterprise-filter-' + providerId);
    const typeSelect = document.getElementById('provider-type-filter-' + providerId);
    if (!grid || !countEl || !monthlyEl || !dailyEl || !countSummaryEl || !section) return;

    const tenantVal = tenantSelect ? tenantSelect.value : '';
    const enterpriseVal = enterpriseSelect ? enterpriseSelect.value : '';
    const typeVal = typeSelect ? typeSelect.value : '';

    const cards = grid.querySelectorAll('.resource-card');
    const baseDaily = parseFloat(section.getAttribute('data-baseline-daily') || '0') || 0;
    const baseCount = parseInt(section.getAttribute('data-baseline-count') || '0', 10) || 0;

    let visible = 0;
    let sumDaily = 0;
    cards.forEach(function (card) {
        const match = cardMatchesTenant(card, tenantVal) &&
            cardMatchesEnterprise(card, enterpriseVal) &&
            cardMatchesType(card, typeVal);
        card.style.display = match ? '' : 'none';
        if (match) {
            visible++;
            sumDaily += parseFloat(card.getAttribute('data-daily-cost') || '0') || 0;
        }
    });

    const noFilters = !tenantVal && !enterpriseVal && !typeVal;
    if (noFilters) {
        sumDaily = baseDaily;
        visible = baseCount;
    }

    monthlyEl.textContent = formatProviderMoney(sumDaily * 30) + ' ₽/месяц';
    dailyEl.textContent = formatProviderMoney(sumDaily) + ' ₽/день';
    countSummaryEl.textContent = visible + ' ресурсов';

    const showFilterHint = !!(tenantVal || enterpriseVal || typeVal);
    countEl.textContent = showFilterHint ? visible + ' из ' + cards.length : '';
}

function onProviderFilterSelectChange(providerId) {
    syncProviderFilterSelects(providerId);
    applyProviderFilters(providerId);
}

function onProviderTenantFilterChange(providerId) {
    onProviderFilterSelectChange(providerId);
}

/** Legacy: optional second arg sets type select then applies */
function filterProviderResources(providerId, typeValue) {
    const typeSelect = document.getElementById('provider-type-filter-' + providerId);
    if (typeof typeValue !== 'undefined' && typeSelect) {
        typeSelect.value = typeValue || '';
    }
    syncProviderFilterSelects(providerId);
    applyProviderFilters(providerId);
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

function toggleK8sLBs(resourceId) {
    const content = document.getElementById(`k8s-lbs-${resourceId}`);
    const chevron = document.getElementById(`k8slb-chevron-${resourceId}`);
    
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

function getCardDetailValue(card, labelText) {
    try {
        const rows = card.querySelectorAll('.detail-row');
        for (const row of rows) {
            const label = row.querySelector('.detail-label')?.textContent?.trim();
            if (label === labelText) {
                return row.querySelector('.detail-value')?.textContent?.trim() || '';
            }
        }
    } catch (e) {
        console.error('Error reading card detail value:', e);
    }
    return '';
}

/** Parse cost string from template. Handles US (1,231.20) and EU (1.231,20) formats. */
function parseCostString(str) {
    if (!str) return 0;
    const cleaned = str.replace(/[^\d.,]/g, '').trim();
    if (!cleaned) return 0;
    const lastComma = cleaned.lastIndexOf(',');
    const lastPeriod = cleaned.lastIndexOf('.');
    if (lastComma > lastPeriod) {
        // EU: comma is decimal (e.g. "1.231,20")
        return parseFloat(cleaned.replace(/\./g, '').replace(',', '.')) || 0;
    }
    // US: period is decimal (e.g. "1,231.20") or no decimal
    return parseFloat(cleaned.replace(/,/g, '')) || 0;
}

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
        ['Провайдер', 'Ресурс', 'Тип', 'Статус', 'External IP', 'Регион', 'Tenant', 'Стоимость день (₽)', 'Стоимость месяц (₽)']
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
                const externalIp = getCardDetailValue(card, 'Внешний IP');
                const region = getCardDetailValue(card, 'Регион');
                const tenant = getCardDetailValue(card, 'Tenant');
                const costMonthly = getCardDetailValue(card, 'Стоимость мес.');
                const costDaily = getCardDetailValue(card, 'Стоимость день');
                const dailyNumeric = parseCostString(costDaily);
                const monthlyNumeric = parseCostString(costMonthly);
                
                resourcesData.push([
                    providerName,
                    resourceName,
                    resourceType,
                    status,
                    externalIp,
                    region,
                    tenant,
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
        { wch: 24 }, // Tenant
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
    csvContent += 'Провайдер,Ресурс,Тип,Статус,External IP,Регион,Tenant,Стоимость день (₽),Стоимость месяц (₽)\n';
    
    providerSections.forEach(section => {
        const providerName = section.querySelector('.provider-name').textContent;
        const resourceCards = section.querySelectorAll('.resource-card');
        
        if (resourceCards.length === 0) {
            csvContent += `"${providerName}","Нет ресурсов","","","","","","",""\n`;
        } else {
            resourceCards.forEach(card => {
                const resourceName = card.querySelector('.resource-name').textContent;
                const resourceType = card.querySelector('.resource-type').textContent;
                const status = card.querySelector('.status-badge').textContent.trim();
                const externalIp = getCardDetailValue(card, 'Внешний IP');
                const region = getCardDetailValue(card, 'Регион');
                const tenant = getCardDetailValue(card, 'Tenant');
                const costDaily = getCardDetailValue(card, 'Стоимость день');
                const costMonthly = getCardDetailValue(card, 'Стоимость мес.');
                const dailyNumeric = parseCostString(costDaily);
                const monthlyNumeric = parseCostString(costMonthly);
                
                csvContent += `"${providerName}","${resourceName}","${resourceType}","${status}","${externalIp}","${region}","${tenant}",${dailyNumeric},${monthlyNumeric}\n`;
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
window.filterProviderResources = filterProviderResources;
window.applyProviderFilters = applyProviderFilters;
window.syncProviderFilterSelects = syncProviderFilterSelects;
window.onProviderFilterSelectChange = onProviderFilterSelectChange;
window.onProviderTenantFilterChange = onProviderTenantFilterChange;
window.toggleUsageSection = toggleUsageSection;
window.toggleCostBreakdown = toggleCostBreakdown;
window.toggleCSIVolumes = toggleCSIVolumes;
window.toggleWorkerVMs = toggleWorkerVMs;
window.exportResourcesToCSV = exportResourcesToCSV;

