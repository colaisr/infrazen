(function() {
  const roles = window.INFRAZEN_DATA?.reportRoles || [];
  let reports = window.INFRAZEN_DATA?.initialReports || [];

  const STATUS_LABELS = {
    in_progress: 'В подготовке',
    ready: 'Готов',
    failed: 'Ошибка'
  };

  const container = document.getElementById('reports-container');
  const generateBtn = document.getElementById('report-generate-btn');
  const defaultGenerateContent = generateBtn?.innerHTML;
  const roleSelect = document.getElementById('report-role-select');

  function groupReportsByRole() {
    const grouped = {};
    for (const role of roles) {
      grouped[role.key] = [];
    }
    reports.forEach((report) => {
      if (!grouped[report.role]) {
        grouped[report.role] = [];
      }
      grouped[report.role].push(report);
    });
    return grouped;
  }

  function formatDate(iso) {
    if (!iso) return '';
    const date = new Date(iso);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function render() {
    const grouped = groupReportsByRole();
    const groups = container?.querySelectorAll('.reports-group');
    groups?.forEach((groupEl) => {
      const role = groupEl.getAttribute('data-role');
      const itemsWrapper = groupEl.querySelector('[data-role-items]');
      if (!itemsWrapper) return;

      const roleReports = (grouped[role] || []).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

      if (!roleReports.length) {
        itemsWrapper.innerHTML = '<div class="reports-empty">Отчетов пока нет. Сгенерируйте первый отчет для этой роли.</div>';
        return;
      }

      itemsWrapper.innerHTML = roleReports.map((report) => {
        const statusClass = `status-pill ${report.status}`;
        const statusLabel = STATUS_LABELS[report.status] || report.status;
        return `
          <div class="report-card" data-report-id="${report.id}">
            <div class="report-card__title">${report.title}</div>
            <div class="report-card__meta">
              <span>${formatDate(report.created_at)}</span>
              <span class="${statusClass}">${statusLabel}</span>
            </div>
            <div class="report-card__actions">
              <button data-action="open" data-report-id="${report.id}">Открыть</button>
              <button data-action="delete" data-report-id="${report.id}" class="report-card__delete">Удалить</button>
            </div>
          </div>
        `;
      }).join('');
    });
  }

  async function fetchReports() {
    try {
      const response = await fetch('/api/reports', { credentials: 'same-origin' });
      const data = await response.json();
      if (data?.success) {
        reports = data.reports || [];
        render();
      }
    } catch (error) {
      console.error('Failed to load reports', error);
    }
  }

  function setGenerateLoading(isLoading) {
    if (!generateBtn) return;
    if (isLoading) {
      generateBtn.disabled = true;
      generateBtn.classList.add('btn--loading');
      generateBtn.innerHTML = `
        <span class="btn-spinner" aria-hidden="true"></span>
        <span>Создание...</span>
      `;
    } else {
      generateBtn.disabled = false;
      generateBtn.classList.remove('btn--loading');
      generateBtn.innerHTML = defaultGenerateContent || 'Сгенерировать';
    }
  }

  async function createReport(roleKey) {
    setGenerateLoading(true);
    try {
      const response = await fetch('/api/reports', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'same-origin',
        body: JSON.stringify({ role: roleKey })
      });
      const data = await response.json();
      if (data?.success && data.report) {
        reports.unshift(data.report);
        render();
      }
    } catch (error) {
      console.error('Failed to create report', error);
    } finally {
      setGenerateLoading(false);
    }
  }

  async function openReport(reportId) {
    try {
      const response = await fetch(`/api/reports/${reportId}`, { credentials: 'same-origin' });
      const data = await response.json();
      if (data?.success && data.report?.content_html) {
        const reportWindow = window.open('', `_report_${reportId}`);
        if (reportWindow) {
          reportWindow.document.write(data.report.content_html);
          reportWindow.document.close();
        }
      }
    } catch (error) {
      console.error('Failed to open report', error);
    }
  }

  async function deleteReport(reportId, button) {
    if (!reportId) return;
    const confirmed = window.confirm('Удалить этот отчет?');
    if (!confirmed) return;

    if (button) {
      button.disabled = true;
      button.classList.add('report-card__delete--loading');
    }
    try {
      const response = await fetch(`/api/reports/${reportId}`, {
        method: 'DELETE',
        credentials: 'same-origin'
      });
      const data = await response.json();
      if (data?.success) {
        reports = reports.filter((report) => String(report.id) !== String(reportId));
        render();
      }
    } catch (error) {
      console.error('Failed to delete report', error);
    } finally {
      if (button) {
        button.disabled = false;
        button.classList.remove('report-card__delete--loading');
      }
    }
  }

  function bindEvents() {
    generateBtn?.addEventListener('click', () => {
      const roleKey = roleSelect?.value;
      if (!roleKey) return;
      createReport(roleKey);
    });

    container?.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.dataset.action === 'open') {
        const reportId = target.dataset.reportId;
        if (reportId) {
          openReport(reportId);
        }
      }
      if (target.dataset.action === 'delete') {
        const reportId = target.dataset.reportId;
        if (reportId) {
          deleteReport(reportId, target);
        }
      }
    });
  }

  function init() {
    render();
    bindEvents();
    fetchReports();
  }

  document.addEventListener('DOMContentLoaded', init);
})();

