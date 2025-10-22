document.addEventListener('DOMContentLoaded', () => {
  initRecoSettings();
});

function initRecoSettings() {
  const root = document.querySelector('.admin-content');
  if (!root) return;
  // Build tabs
  const tabs = document.createElement('div');
  tabs.className = 'reco-tabs';
  tabs.innerHTML = `
    <div class="reco-tab-head">
      <button class="reco-tab-btn active" data-tab="global">Глобальные</button>
      <button class="reco-tab-btn" data-tab="resource">По ресурсам</button>
    </div>
    <div class="reco-tab-body">
      <div id="tab-global" class="reco-panel"></div>
      <div id="tab-resource" class="reco-panel" style="display:none"></div>
    </div>
  `;
  // Insert before existing grid, or at top if grid is absent
  const grid = document.querySelector('.settings-grid');
  if (grid && grid.parentNode) {
    grid.parentNode.insertBefore(tabs, grid);
  } else {
    if (root.firstChild) {
      root.insertBefore(tabs, root.firstChild.nextSibling || root.firstChild);
    } else {
      root.appendChild(tabs);
    }
  }

  tabs.addEventListener('click', (e) => {
    const btn = e.target.closest('.reco-tab-btn');
    if (!btn) return;
    tabs.querySelectorAll('.reco-tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const tab = btn.dataset.tab;
    tabs.querySelectorAll('.reco-panel').forEach(p => p.style.display = 'none');
    document.getElementById(`tab-${tab}`).style.display = '';
  });

  loadRules();
}

function loadRules() {
  // Use bootstrap if available, then refresh via API
  if (window.__RECO_SETTINGS__ && window.__RECO_SETTINGS__.success) {
    renderGlobal(window.__RECO_SETTINGS__.global || []);
    renderResource(window.__RECO_SETTINGS__.resource || []);
  } else {
    // show placeholder until fetch returns
    const ph = document.getElementById('recoSettingsPlaceholder');
    if (ph) ph.style.display = '';
  }

  fetch('/api/admin/recommendations/rules')
    .then(r => r.json())
    .then(data => {
      if (!data.success) throw new Error(data.error || 'Failed');
      const ph = document.getElementById('recoSettingsPlaceholder');
      if (ph) ph.style.display = 'none';
      renderGlobal(data.global || []);
      renderResource(data.resource || []);
    })
    .catch(err => {
      console.error('rules load', err);
    });
}

function renderGlobal(rules) {
  const host = document.getElementById('tab-global');
  host.innerHTML = rules.map(row => ruleRow(row)).join('') || emptyHint();
}

function renderResource(rows) {
  // Build Provider -> ResourceType -> Rules
  const tree = {};
  rows.forEach(r => {
    const provider = r.provider_type || 'any';
    const rtype = r.resource_type || 'any';
    tree[provider] = tree[provider] || {};
    tree[provider][rtype] = tree[provider][rtype] || [];
    tree[provider][rtype].push(r);
  });
  const host = document.getElementById('tab-resource');
  const providers = Object.keys(tree).sort();
  const html = providers.map(p => {
    const pTitle = p === 'any' ? 'Любой провайдер' : p.toUpperCase();
    const rtypes = Object.keys(tree[p]).sort();
    const inner = rtypes.map(rt => {
      const rtTitle = rt === 'any' ? 'Любой ресурс' : rt;
      const rulesHtml = tree[p][rt].map(r => ruleRow(r)).join('');
      const panelId = `panel-${p}-${rt}`.replace(/[^a-zA-Z0-9_-]+/g,'_');
      return `
        <div class="reco-acc">
          <button class="reco-acc-header small" aria-controls="${panelId}" aria-expanded="false" onclick="toggleAcc('${panelId}', this)">
            <span class="reco-acc-caret">▸</span> Ресурс: ${rtTitle}
          </button>
          <div id="${panelId}" class="reco-acc-panel collapsed">
            ${rulesHtml}
          </div>
        </div>
      `;
    }).join('');
    const providerId = `prov-${p}`.replace(/[^a-zA-Z0-9_-]+/g,'_');
    return `
      <div class="reco-acc">
        <button class="reco-acc-header" aria-controls="${providerId}" aria-expanded="true" onclick="toggleAcc('${providerId}', this)">
          <span class="reco-acc-caret">▸</span>
          <span class="reco-provider-title">Провайдер: ${pTitle}</span>
          <span class="reco-info-btn" title="Типы ресурсов" role="button" tabindex="0" onclick="event.stopPropagation(); showProviderTypes('${p}')">ℹ️</span>
        </button>
        <div id="${providerId}" class="reco-acc-panel">
          ${inner}
        </div>
      </div>
    `;
  }).join('');
  host.innerHTML = html || emptyHint();
}

function ruleRow(r) {
  const id = `${r.scope}-${r.rule_id}-${r.provider_type||''}-${r.resource_type||''}`.replace(/[^a-zA-Z0-9_-]+/g,'_');
  const desc = r.description || '';
  return `
    <div class="reco-rule-row">
      <div class="reco-rule-main">
        <div class="reco-rule-title" onclick="toggleDesc(this)">${r.name || r.rule_id}</div>
        ${desc ? `<div class="reco-rule-desc" style="display:none">${escapeHtml(desc)}</div>` : ''}
      </div>
      <div class="reco-rule-action">
        <label class="switch">
          <input id="${id}" type="checkbox" ${r.enabled ? 'checked' : ''} onchange='toggleRule(${JSON.stringify(r)})'>
          <span class="slider"></span>
        </label>
      </div>
    </div>
  `;
}

function toggleRule(r) {
  const payload = {
    rule_id: r.rule_id,
    scope: r.scope,
    provider_type: r.provider_type || null,
    resource_type: r.resource_type || null,
    enabled: !r.enabled,
  };
  fetch('/api/admin/recommendations/rules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(rsp => rsp.json()).then(data => {
    if (!data.success) throw new Error(data.error || 'Failed');
    // reload rules
    loadRules();
  }).catch(err => {
    console.error('toggle rule', err);
    alert('Не удалось сохранить настройку: ' + err.message);
  });
}

function emptyHint() {
  return `<div class="empty-state"><i class="fa-solid fa-circle-info"></i><h3>Нет правил</h3><p>Правила обнаружатся автоматически после загрузки плагинов.</p></div>`;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Simple accordion and description toggles
window.toggleAcc = function(id, btn) {
  const el = document.getElementById(id);
  if (!el) return;
  const expanded = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', (!expanded).toString());
  el.classList.toggle('collapsed', expanded);
}

window.toggleDesc = function(titleEl) {
  const desc = titleEl.nextElementSibling;
  if (!desc) return;
  const isHidden = desc.style.display === 'none' || !desc.style.display;
  desc.style.display = isHidden ? 'block' : 'none';
  titleEl.classList.toggle('expanded', isHidden);
}

window.showProviderTypes = function(provider) {
  fetch(`/api/admin/recommendations/providers/${provider}/resource-types`)
    .then(r => r.json())
    .then(data => {
      if (!data.success) throw new Error(data.error || 'Failed');
      const known = (data.known || []).join(', ') || '—';
      const observed = Object.keys(data.observed || {}).length
        ? Object.entries(data.observed).map(([k,v]) => `${k}: ${v}`).join('\n')
        : '—';
      const effective = (data.effective || []).join(', ') || '—';
      alert(`Провайдер: ${data.provider.toUpperCase()}\n\nИзвестные типы (конфигурация):\n${known}\n\nОбнаруженные в инвентаре:\n${observed}\n\nДоступные к использованию (union):\n${effective}`);
    })
    .catch(err => alert('Ошибка загрузки типов: ' + err.message));
}



