/**
 * Immutable Audit Trail & Change Diff Viewer Component
 */
const AuditViewerComponent = {
  async render(container) {
    container.innerHTML = `
      <div class="animate-fade-in">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
          <div>
            <h1>Immutable Audit Trail & Compliance Log</h1>
            <p class="text-secondary" style="font-size: 0.875rem;">Complete Security Log of Deal Creations, Edits, Cancellations, Approvals & Sync Events</p>
          </div>
          <button class="btn btn-secondary" onclick="AuditViewerComponent.loadData()">
            <span>🔄</span> Refresh Log
          </button>
        </div>

        <div class="card">
          <div class="table-responsive">
            <table class="data-table" id="audit-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Entity Type</th>
                  <th>Target Entity</th>
                  <th>Summary / Notes</th>
                  <th>State Diff</th>
                  <th style="text-align: right;">Undo / Rollback</th>
                </tr>
              </thead>
              <tbody>
                <tr><td colspan="8" style="text-align: center;">Loading audit logs...</td></tr>
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
      const res = await API.getAudit();
      if (!res.success) return;

      const tbody = document.querySelector('#audit-table tbody');
      if (res.audit_events.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No audit events recorded.</td></tr>';
        return;
      }

      tbody.innerHTML = res.audit_events.map(ev => `
        <tr id="audit-row-${ev.id}">
          <td class="font-mono text-muted">${Store.formatDate(ev.timestamp)} ${String(ev.timestamp || '').slice(11, 19)}</td>
          <td><strong>${ev.username || 'system'}</strong></td>
          <td><span class="badge badge-${this.getActionBadge(ev.action)}">${ev.action}</span></td>
          <td><code>${ev.entity_type}</code></td>
          <td class="font-mono"><strong>${ev.entity_name || '#' + ev.entity_id}</strong></td>
          <td>${ev.notes || '-'}</td>
          <td>
            ${(ev.before_state || ev.after_state) ? `
              <button class="btn btn-sm btn-secondary" onclick="AuditViewerComponent.viewDiff(${ev.id})">
                👁️ Diff
              </button>
            ` : '<span class="text-muted">-</span>'}
          </td>
          <td style="text-align: right;">
            ${ev.can_undo ? `
              <button 
                class="btn btn-sm btn-primary"
                onclick="AuditViewerComponent.undoStep(${ev.id}, '${ev.entity_name || ev.entity_type}')"
                style="padding: 4px 10px; font-size: 11px; font-weight: 700; box-shadow: 0 2px 6px rgba(245, 158, 11, 0.2);"
              >
                <span>↩️</span> Undo Step
              </button>
            ` : (ev.undo_state === 'already_undone' ? `
              <span class="text-muted" style="font-size: 11px; font-weight: 600;">✅ Restored</span>
            ` : `
              <span class="text-muted" style="font-size: 11px;">-</span>
            `)}
          </td>
        </tr>
      `).join('');

    } catch (err) {
      Store.showToast('Error loading audit logs: ' + err.message, 'error');
    }
  },

  async undoStep(eventId, entityTitle) {
    if (!confirm(`Are you sure you want to undo action step #${eventId} for ${entityTitle}?`)) {
      return;
    }

    try {
      const res = await API.undoAuditEvent(eventId);
      Store.showToast(res.message || `Action step #${eventId} reversed successfully!`, 'success');
      this.loadData();
    } catch (err) {
      Store.showToast(`Failed to undo step: ${err.message}`, 'error');
    }
  },

  getActionBadge(action) {
    switch (action) {
      case 'CREATE': return 'profit';
      case 'EDIT': return 'ready';
      case 'CANCEL': return 'loss';
      case 'APPROVE': return 'completed';
      case 'PAYMENT': return 'info';
      case 'EXPORT': return 'info';
      case 'BUSY_SYNC': return 'profit';
      default: return 'info';
    }
  },

  async viewDiff(eventId) {
    const res = await API.getAudit();
    if (!res.success) return;

    const ev = res.audit_events.find(e => e.id === eventId);
    if (!ev) return;

    let beforeObj = null;
    let afterObj = null;
    try { if (ev.before_state) beforeObj = JSON.parse(ev.before_state); } catch (e) {}
    try { if (ev.after_state) afterObj = JSON.parse(ev.after_state); } catch (e) {}

    const bodyHtml = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <div>
          <div style="font-weight: 700; color: var(--loss-red); margin-bottom: 8px;">State Before Edit / Event</div>
          <div class="code-box" style="max-height: 380px;">
${beforeObj ? escapeHtml(JSON.stringify(beforeObj, null, 2)) : 'None (Created as new entity)'}
          </div>
        </div>

        <div>
          <div style="font-weight: 700; color: var(--profit-green); margin-bottom: 8px;">State After Edit / Event</div>
          <div class="code-box" style="max-height: 380px;">
${afterObj ? escapeHtml(JSON.stringify(afterObj, null, 2)) : 'None'}
          </div>
        </div>
      </div>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="Store.closeModal()">Close</button>
    `;

    Store.openModal(`Audit Change Diff: ${ev.action} on ${ev.entity_type} #${ev.entity_id}`, bodyHtml, footerHtml);
  }
};
