/**
 * G&C Communication History & Draft Log Viewer Component
 */
const CommViewerComponent = {
  communications: [],
  filters: {
    channel: '',
    status: '',
    search: ''
  },

  async render(container) {
    container.innerHTML = `
      <div class="space-y-4">
        <!-- Header -->
        <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h2 class="page-title" style="display: flex; align-items: center; gap: 8px;">
              <span>💬</span> Communications & Message Log
            </h2>
            <p class="page-subtitle">
              Zero-cost WhatsApp click-to-chat and email mailto: dispatch records and client confirmation tracking.
            </p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="btn btn-secondary" onclick="CommViewerComponent.refresh()">
              🔄 Refresh Log
            </button>
          </div>
        </div>

        <!-- KPI Cards -->
        <div id="comm-kpi-container" class="dashboard-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
          <!-- Populated by updateKPIs -->
        </div>

        <!-- Filter Bar -->
        <div class="card" style="padding: 12px 16px;">
          <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between;">
            <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center;">
              <select id="comm-filter-channel" class="form-select form-select-sm" style="width: 140px;" onchange="CommViewerComponent.applyFilters()">
                <option value="">All Channels</option>
                <option value="whatsapp">📱 WhatsApp</option>
                <option value="email">✉️ Email</option>
              </select>

              <select id="comm-filter-status" class="form-select form-select-sm" style="width: 190px;" onchange="CommViewerComponent.applyFilters()">
                <option value="">All Statuses</option>
                <option value="WhatsApp opened">WhatsApp opened</option>
                <option value="Email draft opened">Email draft opened</option>
                <option value="Manually marked as sent">Manually marked as sent</option>
                <option value="Client confirmed">Client confirmed</option>
                <option value="Client requested amendment">Client requested amendment</option>
                <option value="Failed to open">Failed to open</option>
                <option value="Cancelled before opening">Cancelled before opening</option>
              </select>
            </div>

            <div style="width: 250px;">
              <input type="text" id="comm-filter-search" class="form-control form-control-sm" placeholder="Search party, phone, email..." oninput="CommViewerComponent.applyFilters()">
            </div>
          </div>
        </div>

        <!-- Communications Table -->
        <div class="card" style="padding: 0; overflow: hidden;">
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th style="width: 130px;">Date / Time</th>
                  <th style="width: 100px;">Channel</th>
                  <th>Party & Contact</th>
                  <th>Message Type</th>
                  <th>Subject / Preview</th>
                  <th style="width: 160px;">Status</th>
                  <th style="width: 120px; text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody id="comm-table-body">
                <tr><td colspan="7" class="text-center py-6 text-muted">Loading communications history...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    await this.loadData();
  },

  async loadData() {
    try {
      const res = await API.getCommunications();
      if (res.success) {
        this.communications = res.communications || [];
        this.renderKPIs();
        this.renderTable();
      }
    } catch (err) {
      Store.showToast('Error loading communications: ' + err.message, 'error');
    }
  },

  async refresh() {
    Store.showToast('Refreshing communication history...', 'info');
    await this.loadData();
  },

  renderKPIs() {
    const kpiEl = document.getElementById('comm-kpi-container');
    if (!kpiEl) return;

    const total = this.communications.length;
    const whatsapp = this.communications.filter(c => c.channel === 'whatsapp').length;
    const email = this.communications.filter(c => c.channel === 'email').length;
    const confirmed = this.communications.filter(c => c.status === 'Client confirmed').length;
    const markedSent = this.communications.filter(c => c.status === 'Manually marked as sent').length;

    kpiEl.innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Total Communications</div>
        <div class="stat-value" style="color: var(--text-gold);">${total}</div>
        <div class="stat-meta">Zero-cost outbound logs</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">WhatsApp Drafts</div>
        <div class="stat-value" style="color: #22c55e;">${whatsapp}</div>
        <div class="stat-meta">wa.me click-to-chat</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Email Drafts</div>
        <div class="stat-value" style="color: #3b82f6;">${email}</div>
        <div class="stat-meta">mailto: / webmail</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Client Confirmed</div>
        <div class="stat-value" style="color: var(--profit-green);">${confirmed}</div>
        <div class="stat-meta">${markedSent} marked as sent</div>
      </div>
    `;
  },

  applyFilters() {
    this.filters.channel = document.getElementById('comm-filter-channel')?.value || '';
    this.filters.status = document.getElementById('comm-filter-status')?.value || '';
    this.filters.search = (document.getElementById('comm-filter-search')?.value || '').toLowerCase().trim();
    this.renderTable();
  },

  renderTable() {
    const tbody = document.getElementById('comm-table-body');
    if (!tbody) return;

    let rows = this.communications;

    if (this.filters.channel) {
      rows = rows.filter(r => r.channel === this.filters.channel);
    }
    if (this.filters.status) {
      rows = rows.filter(r => r.status === this.filters.status);
    }
    if (this.filters.search) {
      const q = this.filters.search;
      rows = rows.filter(r =>
        (r.party_name || '').toLowerCase().includes(q) ||
        (r.recipient_contact || '').toLowerCase().includes(q) ||
        (r.subject || '').toLowerCase().includes(q) ||
        (r.message_body || '').toLowerCase().includes(q)
      );
    }

    if (rows.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center py-8 text-muted">
            <div style="font-size: 1.5rem; margin-bottom: 6px;">💬</div>
            <div>No communication records found matching the filters.</div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = rows.map(r => {
      const isWa = r.channel === 'whatsapp';
      const channelBadge = isWa
        ? `<span class="badge" style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3);">📱 WhatsApp</span>`
        : `<span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3);">✉️ Email</span>`;

      let statusBadgeClass = 'badge-secondary';
      if (r.status === 'Client confirmed') statusBadgeClass = 'badge-profit';
      else if (r.status === 'Manually marked as sent') statusBadgeClass = 'badge-info';
      else if (r.status === 'Client requested amendment') statusBadgeClass = 'badge-warning';
      else if (r.status.includes('opened')) statusBadgeClass = 'badge-secondary';

      const dateStr = r.created_at ? r.created_at.slice(0, 16).replace('T', ' ') : '—';
      const typeLabel = (r.message_type || 'Custom').replace(/_/g, ' ').toUpperCase();

      return `
        <tr>
          <td class="font-mono text-secondary" style="font-size: 0.75rem;">${dateStr}</td>
          <td>${channelBadge}</td>
          <td>
            <div style="font-weight: 600; color: var(--text-primary); font-size: 0.8125rem;">${r.party_name}</div>
            <div class="text-muted font-mono" style="font-size: 0.7rem;">${r.recipient_contact}</div>
          </td>
          <td>
            <span class="unit-badge">${typeLabel}</span>
          </td>
          <td>
            <div style="font-weight: 500; font-size: 0.75rem; color: var(--text-gold);">${r.subject || '(No subject)'}</div>
            <div class="text-muted" style="font-size: 0.7rem; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${(r.message_body || '').replace(/\n/g, ' ')}
            </div>
          </td>
          <td>
            <select class="form-select form-select-sm" style="font-size: 0.7rem; padding: 2px 6px;" onchange="CommViewerComponent.updateStatus(${r.id}, this.value)">
              <option value="WhatsApp opened" ${r.status === 'WhatsApp opened' ? 'selected' : ''}>WhatsApp opened</option>
              <option value="Email draft opened" ${r.status === 'Email draft opened' ? 'selected' : ''}>Email draft opened</option>
              <option value="Manually marked as sent" ${r.status === 'Manually marked as sent' ? 'selected' : ''}>Manually marked as sent</option>
              <option value="Client confirmed" ${r.status === 'Client confirmed' ? 'selected' : ''}>Client confirmed</option>
              <option value="Client requested amendment" ${r.status === 'Client requested amendment' ? 'selected' : ''}>Client requested amendment</option>
              <option value="Failed to open" ${r.status === 'Failed to open' ? 'selected' : ''}>Failed to open</option>
              <option value="Cancelled before opening" ${r.status === 'Cancelled before opening' ? 'selected' : ''}>Cancelled before opening</option>
            </select>
          </td>
          <td style="text-align: right;">
            <div style="display: flex; gap: 4px; justify-content: flex-end;">
              <button class="btn btn-sm btn-secondary" style="font-size: 0.7rem; padding: 2px 6px;" onclick="CommViewerComponent.viewMessage(${r.id})" title="View Message Draft">
                👁️ View
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  async updateStatus(id, newStatus) {
    try {
      await API.updateCommunicationStatus(id, { status: newStatus });
      Store.showToast(`Updated status to '${newStatus}'`, 'success');
      const item = this.communications.find(c => c.id === id);
      if (item) item.status = newStatus;
      this.renderKPIs();
    } catch (err) {
      Store.showToast('Failed to update status: ' + err.message, 'error');
    }
  },

  viewMessage(id) {
    const item = this.communications.find(c => c.id === id);
    if (!item) return;

    const existing = document.getElementById('comm-detail-modal');
    if (existing) existing.remove();

    const isWa = item.channel === 'whatsapp';

    const modalHtml = `
      <div id="comm-detail-modal" class="modal-overlay" style="
        position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 9999;
        display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px);
        padding: 20px;
      ">
        <div class="card animate-fade-in" style="
          width: 100%; max-width: 600px; max-height: 85vh; overflow-y: auto;
          background: #1e293b; border: 1px solid var(--border-subtle);
        ">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-subtle); padding-bottom: 10px; margin-bottom: 14px;">
            <h4 style="margin: 0; color: var(--text-gold);">
              ${isWa ? '📱 WhatsApp Message Log' : '✉️ Email Draft Log'} #${item.id}
            </h4>
            <button class="btn btn-sm btn-secondary" onclick="document.getElementById('comm-detail-modal').remove()">✕</button>
          </div>

          <div style="font-size: 0.75rem; margin-bottom: 12px; background: rgba(0,0,0,0.2); padding: 10px; border-radius: var(--radius-sm);">
            <div><strong>Party:</strong> ${item.party_name}</div>
            <div><strong>Recipient:</strong> ${item.recipient_contact}</div>
            <div><strong>Subject:</strong> ${item.subject || '(None)'}</div>
            <div><strong>Logged At:</strong> ${item.created_at}</div>
            <div><strong>Current Status:</strong> <span class="badge badge-info">${item.status}</span></div>
          </div>

          <div class="form-group">
            <label class="form-label" style="font-size: 0.75rem;">Message Body</label>
            <textarea class="form-control font-mono" rows="10" readonly style="font-size: 0.8125rem; white-space: pre-wrap;">${item.message_body}</textarea>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px;">
            <button class="btn btn-sm btn-secondary" onclick="navigator.clipboard.writeText(\`${item.message_body.replace(/`/g, '\\`')}\`); Store.showToast('Copied message content!', 'success');">
              📋 Copy Content
            </button>
            <button class="btn btn-sm btn-primary" onclick="document.getElementById('comm-detail-modal').remove()">
              Close
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
  }
};

window.CommViewerComponent = CommViewerComponent;
