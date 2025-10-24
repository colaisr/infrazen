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
    ['q','provider','status','severity','type','resource_type'].forEach(k=>{
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
            o.textContent = p.provider_type || p.code || p.name; 
            sel.appendChild(o);
        });
    } catch(e) {
        console.error('Error fetching providers:', e);
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
        snoozed:'#a142f4', 
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
    const ctx = [rec.provider_code, rec.resource_name, rec.resource_type].filter(Boolean);
    const chips = ctx.map(x=>`<span class="chip">${x}</span>`).join('');
    const id = rec.id;
    
    // Action buttons for all users (including demo users)
    const actionButtons = `
        <div class="rec-actions">
            <input type="checkbox" class="rowCheck" />
            <button class="btn-icon act" data-act="implemented" title="Отметить внедрённой">✅</button>
            <button class="btn-icon act" data-act="snooze" title="Отложить на 1 месяц">⏱</button>
            <button class="btn-icon act" data-act="dismiss" title="Скрыть">🗑</button>
        </div>
    `;
    
    return `<div class="rec-card" data-id="${id}">
        <div class="rec-head">
            ${sev}
            <div class="rec-title" title="${rec.title}">${rec.title}</div>
        </div>
        <div class="kpi">Экономия/мес: ${formatMoney(rec.estimated_monthly_savings)}</div>
        <div class="rec-context">${chips}</div>
        ${actionButtons}
        <div class="rec-body">${(rec.description||'').slice(0,220)}${(rec.description||'').length>220?'…':''}
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
        
        // Store all recommendations for client-side filtering
        state.allRecommendations = data.items || [];
        
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
    
    const res = await fetch(`/api/recommendations/${id}`);
    const rec = await res.json();
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
    
    box.dataset.loaded = '1';
    box.style.display = 'block';
}

// ============================================================================
// CSV Export
// ============================================================================

function exportToCSV() {
    if (!state.allRecommendations || state.allRecommendations.length === 0) {
        alert('Нет данных для экспорта');
        return;
    }
    
    // Apply current filters to get the filtered data
    let items = state.allRecommendations;
    const searchTerm = qs('#search')?.value?.trim();
    if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        items = items.filter(rec => 
            (rec.title || '').toLowerCase().includes(searchLower) ||
            (rec.description || '').toLowerCase().includes(searchLower) ||
            (rec.resource_name || '').toLowerCase().includes(searchLower)
        );
    }
    
    // Apply other filters
    const provider = qs('#provider')?.value;
    const status = qs('#status')?.value;
    const severity = qs('#severity')?.value;
    const type = qs('#type')?.value;
    const resourceType = qs('#resource_type')?.value;
    
    if (provider) {
        items = items.filter(rec => rec.provider_id == provider);
    }
    if (status) {
        items = items.filter(rec => rec.status === status);
    }
    if (severity) {
        items = items.filter(rec => rec.severity === severity);
    }
    if (type) {
        items = items.filter(rec => rec.recommendation_type === type);
    }
    if (resourceType) {
        items = items.filter(rec => rec.resource_type === resourceType);
    }
    
    if (items.length === 0) {
        alert('Нет данных для экспорта после применения фильтров');
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
    ['#provider','#status','#severity','#type','#resource_type'].forEach(sel=>{
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
        }
    });
}

// ============================================================================
// Initialization
// ============================================================================

(async function(){
    try {
        await fetchProviders();
        const urlp = new URLSearchParams(location.search);
        ['q','provider','status','severity','type','resource_type'].forEach(k=>{ 
            if(urlp.get(k)) {
                const el = qs('#'+k);
                if (el) el.value = urlp.get(k);
            }
        });
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

