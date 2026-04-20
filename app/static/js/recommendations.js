/**
 * InfraZen - Recommendations Page JavaScript
 * Handles recommendation filtering, actions, and export
 */

// ============================================================================
// Utility Functions
// ============================================================================

const qs = (s, el=document) => el.querySelector(s);
const qsa = (s, el=document) => Array.from(el.querySelectorAll(s));

// ============================================================================
// State Management
// ============================================================================

const state = { 
    page: 1, 
    page_size: 25, 
    order_by: '-estimated_monthly_savings',
    total: 0,
    allRecommendations: []
};

// Get isDemoUser from global data
let isDemoUser = false;
if (window.INFRAZEN_DATA && window.INFRAZEN_DATA.isDemoUser) {
    isDemoUser = window.INFRAZEN_DATA.isDemoUser;
}

// ============================================================================
// Query Building
// ============================================================================

function buildQuery(){
    const params = new URLSearchParams();
    ['q','provider','status','severity','type','resource_type','tenant','enterprise_project'].forEach(k=>{
        const v = qs('#'+k)?.value?.trim(); 
        if(v) params.set(k, v);
    });
    params.set('page', state.page); 
    params.set('page_size', state.page_size); 
    params.set('order_by', state.order_by);
    history.replaceState(null, '', '?'+params.toString());
    return params.toString();
}

// ============================================================================
// Data Fetching
// ============================================================================

async function fetchProviders(){
    try {
        const res = await fetch('/api/providers');
        const data = await res.json();
        const sel = qs('#provider');
        (data.providers || []).forEach(p=>{
            const o = document.createElement('option'); 
            o.value = p.id; 
            o.textContent = p.name || p.provider_type || p.code || String(p.id); 
            sel.appendChild(o);
        });
    } catch(e) {
        console.error('Error fetching providers:', e);
    }
}

async function fetchRecommendationFilterOptions(){
    try {
        const res = await fetch('/api/recommendations/filter-options');
        if (!res.ok) return;
        const data = await res.json();
        const tenantSel = qs('#tenant');
        const entSel = qs('#enterprise_project');
        if (!tenantSel || !entSel) return;
        const keepTenant = tenantSel.value;
        const keepEnt = entSel.value;
        while (tenantSel.options.length > 1) tenantSel.remove(1);
        while (entSel.options.length > 1) entSel.remove(1);
        (data.tenants || []).forEach(t => {
            const o = document.createElement('option');
            o.value = t;
            o.textContent = t;
            tenantSel.appendChild(o);
        });
        (data.enterprise_projects || []).forEach(ep => {
            const o = document.createElement('option');
            o.value = ep;
            o.textContent = ep;
            entSel.appendChild(o);
        });
        if (keepTenant) tenantSel.value = keepTenant;
        if (keepEnt) entSel.value = keepEnt;
    } catch (e) {
        console.error('Error fetching recommendation filter options:', e);
    }
}

// ============================================================================
// UI Helpers
// ============================================================================

function sevClass(sev){
    return {
        critical:'sev-critical', 
        high:'sev-high', 
        medium:'sev-medium', 
        low:'sev-low', 
        info:'sev-info'
    }[sev] || 'sev-info';
}

function statusBadge(st){
    const colors = {
        pending:'#1a73e8', 
        implemented:'#34a853', 
        dismissed:'#9aa0a6'
    };
    const c = colors[st]||'#5f6368';
    return `<span style="display:inline-block;padding:2px 8px;border-radius:12px;background:${c}20;color:${c};text-transform:capitalize;">${st}</span>`;
}

function formatMoney(v){
    const n = Number(v||0); 
    return new Intl.NumberFormat('ru-RU', {
        style:'currency', 
        currency:'RUB', 
        maximumFractionDigits:0
    }).format(n);
}

// ============================================================================
// Card Rendering
// ============================================================================

function cardTemplate(rec){
    const created = rec.created_at? new Date(rec.created_at).toLocaleString('ru-RU') : '';
    const sev = `<span class="sev-dot ${sevClass(rec.severity)}"></span>`;
    const id = rec.id;
    
    // Small provider logo/icon for connection badge with tooltip
    const providerLogo = {
        'yandex': '<span class="provider-logo" style="background:#FF3333" title="Yandex Cloud">Y</span>',
        'selectel': '<span class="provider-logo" style="background:#0066FF" title="Selectel">S</span>',
        'beget': '<span class="provider-logo" style="background:#8B5CF6" title="Beget">B</span>'
    }[rec.provider_code?.toLowerCase()] || '<span class="provider-logo" style="background:#94a3b8" title="Неизвестный провайдер">?</span>';
    
    // Resource type icon (FontAwesome for professional look)
    const resourceTypeMap = {
        'server': { icon: 'fa-server', label: 'Сервер' },
        'vm': { icon: 'fa-server', label: 'Виртуальная машина' },
        'volume': { icon: 'fa-hard-drive', label: 'Том' },
        'disk': { icon: 'fa-hard-drive', label: 'Диск' },
        'database': { icon: 'fa-database', label: 'База данных' },
        'postgresql': { icon: 'fa-database', label: 'PostgreSQL' },
        'mysql': { icon: 'fa-database', label: 'MySQL' },
        'redis': { icon: 'fa-database', label: 'Redis' },
        'kafka': { icon: 'fa-stream', label: 'Kafka' },
        'kubernetes': { icon: 'fa-docker', label: 'Kubernetes' },
        'snapshot': { icon: 'fa-camera', label: 'Снапшот' },
        'image': { icon: 'fa-compact-disc', label: 'Образ' },
        'ip': { icon: 'fa-network-wired', label: 'IP-адрес' },
        'dns': { icon: 'fa-globe', label: 'DNS' },
        'container_registry': { icon: 'fa-box', label: 'Container Registry' }
    };
    
    const resourceType = rec.resource_type?.toLowerCase() || 'unknown';
    const typeInfo = resourceTypeMap[resourceType] || { icon: 'fa-cube', label: rec.resource_type || 'Ресурс' };
    const resourceTypeIcon = `<i class="fa-solid ${typeInfo.icon}" title="${typeInfo.label}"></i>`;
    
    // Connection name from provider metadata (most important!)
    const connectionName = rec.connection_name || rec.provider_code || 'Unknown';
    
    // Clean resource line: [Provider-logo Connection] > Icon Resource-name
    const resourceLine = `
        <div class="resource-line">
            <span class="connection-badge">${providerLogo} ${connectionName}</span>
            <span class="separator">›</span>
            <span class="resource-icon">${resourceTypeIcon}</span>
            <span class="resource-name" title="${rec.resource_name || 'Unknown'}">${rec.resource_name || 'Unknown'}</span>
        </div>
    `;
    
    // Action buttons for all users (including demo users)
    const actionButtons = `
        <div class="rec-actions">
            <input type="checkbox" class="rowCheck" />
            <button class="btn-icon act" data-act="implemented" title="Отметить внедрённой">✅</button>
            <button class="btn-icon act" data-act="dismiss" title="Скрыть">🗑</button>
        </div>
    `;
    
    return `<div class="rec-card" data-id="${id}">
        <div class="rec-head">
            ${sev}
            <div class="rec-title" title="${rec.title}">${rec.title}</div>
        </div>
        <div class="kpi">Экономия/мес: ${formatMoney(rec.estimated_monthly_savings)}</div>
        ${resourceLine}
        ${actionButtons}
        <div class="rec-body" id="body-${id}">
            <div class="rec-description">${rec.ai_short_description || (rec.description||'').slice(0,220)}${(!rec.ai_short_description && (rec.description||'').length>220)?'…':''}</div>
            <button class="link-btn more" data-id="${id}">Подробнее</button>
        </div>
        <div class="rec-details" id="details-${id}"></div>
        <div class="rec-footer">
            <span>${statusBadge(rec.status)}</span>
            <span>${created}</span>
        </div>
    </div>`;
}

// ============================================================================
// Data Loading
// ============================================================================

async function load(){
    try {
        const queryString = buildQuery();
        const res = await fetch('/api/recommendations?'+queryString);
        
        if (!res.ok) {
            throw new Error(`API request failed with status ${res.status}`);
        }
        
        const data = await res.json();
        const list = qs('#recsList');
        if (!list) {
            console.error('Recommendations list container not found');
            return;
        }
        
        state.allRecommendations = data.items || [];
        state.total = data.total || 0;
        
        // Apply client-side search filter if search term exists
        let items = data.items || [];
        const searchTerm = qs('#search')?.value?.trim();
        if (searchTerm) {
            const searchLower = searchTerm.toLowerCase();
            items = items.filter(rec => 
                (rec.title || '').toLowerCase().includes(searchLower) ||
                (rec.description || '').toLowerCase().includes(searchLower) ||
                (rec.resource_name || '').toLowerCase().includes(searchLower)
            );
        }
        
        if (items.length === 0) {
            list.innerHTML = '<div style="padding: 2rem; text-align: center; color: #666;">Рекомендации не найдены. Попробуйте изменить фильтры или обновить страницу.</div>';
        } else {
            list.innerHTML = items.map(cardTemplate).join('');
        }
        
        renderPagination(data.page, data.page_size, data.total);
        enableBulkButtons();
    } catch (error) {
        console.error('Error in load function:', error);
        const list = qs('#recsList');
        if (list) {
            list.innerHTML = '<div style="padding: 2rem; text-align: center; color: #d32f2f;">Ошибка загрузки рекомендаций: ' + error.message + '</div>';
        }
    }
}

// ============================================================================
// Pagination
// ============================================================================

function renderPagination(page, pageSize, total) {
    const container = qs('#recPagination');
    const infoEl = qs('#recPaginationInfo');
    const prevBtn = qs('#recPagePrev');
    const nextBtn = qs('#recPageNext');
    if (!container || !infoEl) return;
    
    if (total <= pageSize) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'flex';
    const totalPages = Math.ceil(total / pageSize);
    const from = (page - 1) * pageSize + 1;
    const to = Math.min(page * pageSize, total);
    
    infoEl.textContent = `Показано ${from}–${to} из ${total}`;
    prevBtn.disabled = page <= 1;
    nextBtn.disabled = page >= totalPages;
}

// ============================================================================
// Filtering
// ============================================================================

function filterRecommendations() {
    const list = qs('#recsList');
    if (!list || !state.allRecommendations) return;
    
    const searchTerm = qs('#search')?.value?.trim();
    let items = state.allRecommendations;
    
    if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        items = items.filter(rec => 
            (rec.title || '').toLowerCase().includes(searchLower) ||
            (rec.description || '').toLowerCase().includes(searchLower) ||
            (rec.resource_name || '').toLowerCase().includes(searchLower)
        );
    }
    
    if (items.length === 0) {
        list.innerHTML = '<div style="padding: 2rem; text-align: center; color: #666;">Рекомендации не найдены. Попробуйте изменить фильтры или обновить страницу.</div>';
    } else {
        list.innerHTML = items.map(cardTemplate).join('');
    }
    
    enableBulkButtons();
}

// ============================================================================
// Actions
// ============================================================================

async function actOne(id, action, extra={}){
    const res = await fetch(`/api/recommendations/${id}/action`, {
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body: JSON.stringify({action, ...extra})
    });
    if(res.ok) await load();
}

function selectedIds(){
    return qsa('.rowCheck:checked').map(cb=>cb.closest('.rec-card').dataset.id);
}

async function actBulk(action){
    const ids = selectedIds(); 
    if(!ids.length) return;
    const res = await fetch('/api/recommendations/bulk', {
        method:'POST', 
        headers:{'Content-Type':'application/json'}, 
        body: JSON.stringify({ids, action})
    });
    if(res.ok) await load();
}

function enableBulkButtons(){
    const has = selectedIds().length>0;
    // Bulk button logic can be added here
}

// ============================================================================
// Details Toggle
// ============================================================================

async function toggleDetails(id){
    const box = qs(`#details-${id}`);
    if(!box) return;
    
    if(box.dataset.loaded === '1'){
        box.style.display = box.style.display === 'none' ? 'block' : 'none';
        return;
    }
    
    // Fetch full recommendation data
    const res = await fetch(`/api/recommendations/${id}`);
    const rec = await res.json();
    
    // If AI-generated text is available, use it
    if (rec.ai_detailed_description && window.INFRAZEN_DATA?.enableAIRecommendations) {
        box.innerHTML = `
            <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px; margin-top: 0.5rem;">
                <div style="font-size: 14px; line-height: 1.6; color: #1f2937; margin-bottom: 1rem;">
                    ${rec.ai_detailed_description}
                </div>
                <button class="btn btn-primary chat-with-finops-btn" style="font-size: 14px; padding: 8px 16px; display: inline-flex; align-items: center; gap: 6px;">
                    💬 Обсудить с FinOps
                </button>
            </div>
        `;
    } else {
        // Fallback to original insights/metrics display
        const insights = rec.insights || '';
        const metrics = rec.metrics_snapshot || '';
        
        box.innerHTML = `
            <div class="rec-split">
                <div>
                    <div style="font-weight:600; margin-bottom:4px;">Пояснения</div>
                    <pre style="white-space:pre-wrap;background:#f6f7f9;border:1px solid #e0e3e7;border-radius:8px;padding:8px;">${insights}</pre>
                </div>
                <div>
                    <div style="font-weight:600; margin-bottom:4px;">Метрики</div>
                    <pre style="white-space:pre-wrap;background:#f6f7f9;border:1px solid #e0e3e7;border-radius:8px;padding:8px;">${metrics}</pre>
                </div>
            </div>`;
    }
    
    box.dataset.loaded = '1';
    box.style.display = 'block';
}

// ============================================================================
// CSV Export
// ============================================================================

async function exportToCSV() {
    // Fetch all pages for current filters to export complete dataset
    let items = [];
    let page = 1;
    const pageSize = 200;
    let hasMore = true;
    while (hasMore) {
        const params = new URLSearchParams();
        ['q','provider','status','severity','type','resource_type','tenant','enterprise_project'].forEach(k=>{
            const v = qs('#'+k)?.value?.trim();
            if(v) params.set(k, v);
        });
        params.set('page', page);
        params.set('page_size', pageSize);
        params.set('order_by', state.order_by);
        const res = await fetch('/api/recommendations?'+params.toString());
        const data = await res.json();
        items = items.concat(data.items || []);
        hasMore = (data.items?.length || 0) >= pageSize && items.length < (data.total || 0);
        page++;
    }
    
    if (!items || items.length === 0) {
        alert('Нет данных для экспорта');
        return;
    }
    
    // Apply client-side search filter (API doesn't support q for recommendations)
    const searchTerm = qs('#search')?.value?.trim();
    if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        items = items.filter(rec => 
            (rec.title || '').toLowerCase().includes(searchLower) ||
            (rec.description || '').toLowerCase().includes(searchLower) ||
            (rec.resource_name || '').toLowerCase().includes(searchLower)
        );
    }
    
    if (items.length === 0) {
        alert('Нет данных для экспорта после применения поиска');
        return;
    }
    
    // Create CSV content
    const headers = [
        'ID',
        'Название',
        'Описание', 
        'Провайдер',
        'Ресурс',
        'Тип ресурса',
        'Тип рекомендации',
        'Важность',
        'Статус',
        'Экономия/мес (₽)',
        'Потенциальная экономия (₽)',
        'Дата создания'
    ];
    
    const csvContent = [
        headers.join(','),
        ...items.map(rec => [
            rec.id || '',
            `"${(rec.title || '').replace(/"/g, '""')}"`,
            `"${(rec.description || '').replace(/"/g, '""')}"`,
            rec.provider_code || '',
            rec.resource_name || '',
            rec.resource_type || '',
            rec.recommendation_type || '',
            rec.severity || '',
            rec.status || '',
            rec.estimated_monthly_savings || 0,
            rec.potential_savings || 0,
            rec.created_at ? new Date(rec.created_at).toLocaleDateString('ru-RU') : ''
        ].join(','))
    ].join('\n');
    
    // Create and download file
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `recommendations_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ============================================================================
// Event Listeners
// ============================================================================

function initializeEventListeners() {
    // Filter change events
    ['#provider','#status','#severity','#type','#resource_type','#tenant','#enterprise_project'].forEach(sel=>{
        const element = qs(sel);
        if (element) {
            element.addEventListener('change', ()=>{state.page=1; load();});
        }
    });
    
    // Checkbox change events for bulk actions
    document.addEventListener('change', (e) => {
        if (e.target.classList.contains('rowCheck')) {
            enableBulkButtons();
        }
    });
    
    // Search input with debounce
    const searchInput = qs('#search');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', ()=>{
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(()=>{
                filterRecommendations();
            }, 300);
        });
        searchInput.addEventListener('change', ()=>{
            filterRecommendations();
        });
    }
    
    // Select all checkbox
    const selectAll = qs('#selectAll');
    if (selectAll) {
        selectAll.addEventListener('change', (e)=>{ 
            qsa('.rowCheck').forEach(cb=>cb.checked=e.target.checked); 
            enableBulkButtons(); 
        });
    }
    
    // CSV export button
    const exportCsv = qs('#exportCsv');
    if (exportCsv) {
        exportCsv.addEventListener('click', exportToCSV);
    }
    
    // Pagination
    const prevBtn = qs('#recPagePrev');
    const nextBtn = qs('#recPageNext');
    if (prevBtn) {
        prevBtn.addEventListener('click', () => { state.page = Math.max(1, state.page - 1); load(); });
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            const maxPage = Math.ceil(state.total / state.page_size) || 1;
            state.page = Math.min(maxPage, state.page + 1);
            load();
        });
    }
    
    // Recommendation action buttons and details toggle
    document.addEventListener('click', (e)=>{
        if(e.target.classList.contains('act')){ 
            e.preventDefault(); 
            const id = e.target.closest('.rec-card').dataset.id; 
            actOne(id, e.target.dataset.act); 
        }
        if(e.target.classList.contains('more')){ 
            e.preventDefault(); 
            const id = e.target.dataset.id; 
            toggleDetails(id);
            e.target.blur(); // Remove focus to clear the blue border
        }
    });
}

// ============================================================================
// Initialization
// ============================================================================

(async function(){
    try {
        await fetchProviders();
        await fetchRecommendationFilterOptions();
        const urlp = new URLSearchParams(location.search);
        ['q','provider','status','severity','type','resource_type','tenant','enterprise_project'].forEach(k=>{ 
            if(urlp.get(k)) {
                const el = qs('#'+k);
                if (el) el.value = urlp.get(k);
            }
        });
        const pageParam = urlp.get('page');
        if (pageParam) state.page = Math.max(1, parseInt(pageParam, 10) || 1);
        initializeEventListeners();
        await load();
    } catch (error) {
        console.error('Error loading recommendations:', error);
        const list = qs('#recsList');
        if (list) {
            list.innerHTML = '<div style="padding: 2rem; text-align: center; color: #666;">Ошибка загрузки рекомендаций. Попробуйте обновить страницу.</div>';
        }
    }
})();

