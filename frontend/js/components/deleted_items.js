/**
 * G&C Central Deal and Brokerage Automation Platform
 * Component: Deleted Items & Step-by-Step Deletion / Undo Action Log
 */
const DeletedItemsComponent = {
  activeViewMode: 'log', // 'log' or 'matrix'
  activeTypeFilter: 'all',
  searchQuery: '',
  auditLogs: [],
  rawTrashItems: [],

  async render(container) {
    container.innerHTML = `
      <div class="animate-fade-in">
        <!-- Header Banner -->
        <div class="card" style="margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
            <div>
              <h1 class="page-title" style="margin-bottom: 6px; display: flex; align-items: center; gap: 10px;">
                <span>🗑️</span> Deletion Log & Undo Action History
              </h1>
              <p class="page-subtitle">
                Complete changelog of all deletion and cancellation steps. Review the audit history and click <strong>"↩️ Undo This Step"</strong> to instantly reverse any deletion.
              </p>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
              <button id="refresh-trash-btn" class="btn btn-secondary btn-sm">
                <span>🔄</span> Refresh Log
              </button>
            </div>
          </div>

          <!-- Top View Mode Switcher -->
          <div style="display: flex; gap: 12px; margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border-subtle); flex-wrap: wrap; align-items: center; justify-content: space-between;">
            <div style="display: flex; gap: 8px;" id="trash-view-modes">
              <button class="btn btn-sm ${this.activeViewMode === 'log' ? 'btn-primary' : 'btn-secondary'}" data-mode="log">
                <span>📜</span> Step-by-Step Deletion Log & Undo
              </button>
              <button class="btn btn-sm ${this.activeViewMode === 'matrix' ? 'btn-primary' : 'btn-secondary'}" data-mode="matrix">
                <span>📦</span> Active Recycle Bin Items (<span id="count-all">0</span>)
              </button>
            </div>

            <!-- Entity Category Filter -->
            <div style="display: flex; gap: 6px; flex-wrap: wrap;" id="trash-filter-tabs">
              <button class="btn btn-sm ${this.activeTypeFilter === 'all' ? 'btn-outline-gold active' : 'btn-secondary'}" data-type="all">
                All (<span id="badge-count-all">...</span>)
              </button>
              <button class="btn btn-sm ${this.activeTypeFilter === 'deals' ? 'btn-outline-gold active' : 'btn-secondary'}" data-type="deals">
                Deals (<span id="badge-count-deals">...</span>)
              </button>
              <button class="btn btn-sm ${this.activeTypeFilter === 'chains' ? 'btn-outline-gold active' : 'btn-secondary'}" data-type="chains">
                Chains (<span id="badge-count-chains">...</span>)
              </button>
              <button class="btn btn-sm ${this.activeTypeFilter === 'parties' ? 'btn-outline-gold active' : 'btn-secondary'}" data-type="parties">
                Parties (<span id="badge-count-parties">...</span>)
              </button>
              <button class="btn btn-sm ${this.activeTypeFilter === 'products' ? 'btn-outline-gold active' : 'btn-secondary'}" data-type="products">
                Products (<span id="badge-count-products">...</span>)
              </button>
              <button class="btn btn-sm ${this.activeTypeFilter === 'payments' ? 'btn-outline-gold active' : 'btn-secondary'}" data-type="payments">
                Payments (<span id="badge-count-payments">...</span>)
              </button>
            </div>
          </div>
        </div>

        <!-- Main Content Area -->
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <h2 id="trash-section-title" style="font-size: 16px; font-weight: 700; color: var(--text-primary);">
                ${this.activeViewMode === 'log' ? '📜 Step Action Log (Click "Undo Step" to restore)' : '📦 Currently Deleted Items Ready to Restore'}
              </h2>
            </div>
            <div style="max-width: 320px; width: 100%;">
              <input type="text" id="trash-search-input" class="form-control" placeholder="Search by step ID, name, user, or reason..." value="${this.searchQuery}">
            </div>
          </div>

          <div id="trash-display-container">
            <div style="text-align: center; padding: 40px; color: var(--text-muted);">
              <div class="spinner" style="margin-bottom: 12px;"></div>
              <div>Loading log entries...</div>
            </div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents(container);
    await this.loadData(container);
  },

  bindEvents(container) {
    container.querySelector('#refresh-trash-btn')?.addEventListener('click', () => {
      this.loadData(container);
    });

    const modeBtns = container.querySelectorAll('#trash-view-modes button');
    modeBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeViewMode = btn.getAttribute('data-mode');
        modeBtns.forEach(b => {
          b.className = `btn btn-sm ${b.getAttribute('data-mode') === this.activeViewMode ? 'btn-primary' : 'btn-secondary'}`;
        });
        const titleEl = container.querySelector('#trash-section-title');
        if (titleEl) {
          titleEl.textContent = this.activeViewMode === 'log' 
            ? '📜 Step Action Log (Click "Undo Step" to restore)' 
            : '📦 Currently Deleted Items Ready to Restore';
        }
        this.renderCurrentView(container);
      });
    });

    const filterTabs = container.querySelectorAll('#trash-filter-tabs button');
    filterTabs.forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTypeFilter = btn.getAttribute('data-type');
        filterTabs.forEach(b => {
          const isActive = b.getAttribute('data-type') === this.activeTypeFilter;
          b.className = `btn btn-sm ${isActive ? 'btn-outline-gold active' : 'btn-secondary'}`;
        });
        this.renderCurrentView(container);
      });
    });

    const searchInput = container.querySelector('#trash-search-input');
    searchInput?.addEventListener('input', (e) => {
      this.searchQuery = e.target.value.toLowerCase().trim();
      this.renderCurrentView(container);
    });
  },

  async loadData(container) {
    try {
      // Fetch both trash items and audit logs
      const [trashRes, auditRes] = await Promise.all([
        API.getTrash('all'),
        API.getAuditTrail({ limit: 150 })
      ]);

      this.rawTrashItems = trashRes.deleted_items || [];
      this.auditLogs = (auditRes.audit_events || []).filter(e => 
        e.action === 'DELETE' || e.action === 'CANCEL' || e.action === 'RESTORE'
      );

      // Compute badge counts
      const allItems = this.rawTrashItems;
      const counts = {
        all: allItems.length,
        deals: allItems.filter(x => x.entity_type === 'deal').length,
        chains: allItems.filter(x => x.entity_type === 'chain').length,
        parties: allItems.filter(x => x.entity_type === 'party').length,
        products: allItems.filter(x => x.entity_type === 'product').length,
        payments: allItems.filter(x => x.entity_type === 'payment').length
      };

      const countAllEl = container.querySelector('#count-all');
      if (countAllEl) countAllEl.textContent = counts.all;

      Object.keys(counts).forEach(k => {
        const badge = container.querySelector(`#badge-count-${k}`);
        if (badge) badge.textContent = counts[k];
      });

      // Update sidebar badge
      const sidebarBadge = document.getElementById('sidebar-trash-count');
      if (sidebarBadge) {
        sidebarBadge.textContent = counts.all > 0 ? counts.all : '';
        sidebarBadge.style.display = counts.all > 0 ? 'inline-block' : 'none';
      }

      this.renderCurrentView(container);
    } catch (err) {
      const display = container.querySelector('#trash-display-container');
      if (display) {
        display.innerHTML = `
          <div class="alert alert-danger" style="margin: 20px 0;">
            Failed to load log entries: ${err.message}
          </div>
        `;
      }
    }
  },

  renderCurrentView(container) {
    if (this.activeViewMode === 'log') {
      this.renderLogView(container);
    } else {
      this.renderMatrixView(container);
    }
  },

  renderLogView(container) {
    const display = container.querySelector('#trash-display-container');
    if (!display) return;

    let filtered = this.auditLogs;

    // Filter by entity type if needed
    if (this.activeTypeFilter !== 'all') {
      const targetType = this.activeTypeFilter.replace(/s$/, ''); // deals -> deal
      filtered = filtered.filter(e => {
        const et = (e.entity_type || '').toLowerCase();
        if (targetType === 'deal') return et === 'deal';
        if (targetType === 'chain') return et.includes('chain');
        if (targetType === 'partie' || targetType === 'party') return et === 'party';
        if (targetType === 'product') return et === 'product';
        if (targetType === 'payment') return et.includes('payment');
        return true;
      });
    }

    // Filter by search query
    if (this.searchQuery) {
      filtered = filtered.filter(e => {
        return (
          String(e.id).includes(this.searchQuery) ||
          (e.action && e.action.toLowerCase().includes(this.searchQuery)) ||
          (e.username && e.username.toLowerCase().includes(this.searchQuery)) ||
          (e.entity_name && e.entity_name.toLowerCase().includes(this.searchQuery)) ||
          (e.notes && e.notes.toLowerCase().includes(this.searchQuery)) ||
          (e.entity_type && e.entity_type.toLowerCase().includes(this.searchQuery))
        );
      });
    }

    if (filtered.length === 0) {
      display.innerHTML = `
        <div style="text-align: center; padding: 60px 20px; color: var(--text-muted);">
          <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.7;">📜</div>
          <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">No Deletion / Change Steps Found</h3>
          <p style="font-size: 13px; max-width: 420px; margin: 0 auto;">Whenever you delete or modify any transaction or lot, the exact step is recorded here so you can undo that step anytime.</p>
        </div>
      `;
      return;
    }

    display.innerHTML = `
      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 80px;">Step #</th>
              <th style="width: 150px;">Time</th>
              <th style="width: 120px;">User</th>
              <th style="width: 110px;">Action</th>
              <th style="width: 110px;">Entity</th>
              <th>Target & Deletion Reason</th>
              <th style="width: 150px;">Current State</th>
              <th style="width: 150px; text-align: right;">Undo Action</th>
            </tr>
          </thead>
          <tbody>
            ${filtered.map(ev => {
              const isDelete = ev.action === 'DELETE';
              const isCancel = ev.action === 'CANCEL';
              const isRestore = ev.action === 'RESTORE';
              const canUndo = ev.can_undo;

              let actionBadge = `<span class="badge badge-info">${ev.action}</span>`;
              if (isDelete) actionBadge = `<span class="badge badge-loss" style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4);">🗑️ DELETE</span>`;
              if (isCancel) actionBadge = `<span class="badge badge-loss">🚫 CANCEL</span>`;
              if (isRestore) actionBadge = `<span class="badge badge-profit" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4);">↩️ RESTORE</span>`;

              let stateBadge = `<span class="badge badge-draft">Info Logged</span>`;
              if (ev.undo_state === 'pending_undo') {
                stateBadge = `<span class="badge badge-warning" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4);">🗑️ Currently Deleted</span>`;
              } else if (ev.undo_state === 'already_undone') {
                stateBadge = `<span class="badge badge-profit" style="background: rgba(16, 185, 129, 0.15); color: #34d399;">✅ Active / Restored</span>`;
              }

              return `
                <tr id="log-step-row-${ev.id}">
                  <td class="font-mono text-gold" style="font-weight: 700;">#${ev.id}</td>
                  <td>
                    <span style="font-size: 12px; font-family: var(--font-mono); color: var(--text-muted);">
                      ${ev.timestamp ? new Date(ev.timestamp).toLocaleString('en-IN') : 'Recent'}
                    </span>
                  </td>
                  <td><strong>${ev.username || 'admin'}</strong></td>
                  <td>${actionBadge}</td>
                  <td><code>${ev.entity_type}</code></td>
                  <td>
                    <div style="font-weight: 700; color: var(--text-primary); font-size: 13px;">
                      ${ev.entity_name || `${ev.entity_type.toUpperCase()} #${ev.entity_id}`}
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
                      ${ev.notes || 'User performed action'}
                    </div>
                  </td>
                  <td>${stateBadge}</td>
                  <td style="text-align: right;">
                    ${canUndo ? `
                      <button 
                        class="btn btn-primary btn-sm undo-step-btn"
                        data-event-id="${ev.id}"
                        data-title="${ev.entity_name || ev.entity_type}"
                        style="padding: 5px 12px; font-size: 12px; font-weight: 700; box-shadow: 0 2px 8px rgba(245, 158, 11, 0.25);"
                      >
                        <span>↩️</span> Undo Step
                      </button>
                    ` : (isDelete || isCancel ? `
                      <span class="text-muted" style="font-size: 12px; font-weight: 600;">
                        ✅ Already Undone
                      </span>
                    ` : `
                      <span class="text-muted" style="font-size: 12px;">-</span>
                    `)}
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;

    // Bind undo buttons
    display.querySelectorAll('.undo-step-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const eventId = btn.getAttribute('data-event-id');
        const title = btn.getAttribute('data-title');

        btn.disabled = true;
        btn.innerHTML = `<span>⏳</span> Undoing...`;

        try {
          const res = await API.undoAuditEvent(eventId);
          Store.showToast(res.message || `Successfully undid step for ${title}!`, 'success');

          // Highlight row
          const row = document.getElementById(`log-step-row-${eventId}`);
          if (row) {
            row.style.background = 'rgba(16, 185, 129, 0.2)';
            row.style.transition = 'all 0.3s ease';
          }

          setTimeout(() => {
            this.loadData(container);
          }, 400);
        } catch (err) {
          Store.showToast(`Failed to undo step: ${err.message}`, 'error');
          btn.disabled = false;
          btn.innerHTML = `<span>↩️</span> Undo Step`;
        }
      });
    });
  },

  renderMatrixView(container) {
    const display = container.querySelector('#trash-display-container');
    if (!display) return;

    let filtered = this.rawTrashItems;
    if (this.activeTypeFilter !== 'all') {
      const targetType = this.activeTypeFilter.replace(/s$/, '');
      filtered = filtered.filter(x => x.entity_type === targetType || (targetType === 'partie' && x.entity_type === 'party'));
    }

    if (this.searchQuery) {
      filtered = filtered.filter(item => {
        return (
          (item.title && item.title.toLowerCase().includes(this.searchQuery)) ||
          (item.summary && item.summary.toLowerCase().includes(this.searchQuery)) ||
          (item.deletion_reason && item.deletion_reason.toLowerCase().includes(this.searchQuery)) ||
          (item.deleted_by && item.deleted_by.toLowerCase().includes(this.searchQuery))
        );
      });
    }

    if (filtered.length === 0) {
      display.innerHTML = `
        <div style="text-align: center; padding: 60px 20px; color: var(--text-muted);">
          <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.7;">✨</div>
          <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">Recycle Bin is Empty</h3>
          <p style="font-size: 13px; max-width: 420px; margin: 0 auto;">No deleted items found in this view. Check the "Step-by-Step Deletion Log" tab above to review all historic actions.</p>
        </div>
      `;
      return;
    }

    const typeBadges = {
      deal: '<span class="badge badge-info">DEAL</span>',
      chain: '<span class="badge badge-warning">DEAL CHAIN</span>',
      party: '<span class="badge badge-success">PARTY</span>',
      product: '<span class="badge badge-info">PRODUCT</span>',
      payment: '<span class="badge badge-success">PAYMENT</span>'
    };

    display.innerHTML = `
      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 110px;">Type</th>
              <th>Deleted Item Title & Summary</th>
              <th style="width: 180px;">Impact / Context</th>
              <th style="width: 160px;">Deleted Time</th>
              <th style="width: 140px;">Deleted By</th>
              <th style="width: 180px;">Reason</th>
              <th style="width: 140px; text-align: right;">Restore Action</th>
            </tr>
          </thead>
          <tbody>
            ${filtered.map(item => `
              <tr id="trash-matrix-row-${item.entity_type}-${item.id}">
                <td>${typeBadges[item.entity_type] || `<span class="badge">${item.entity_type.toUpperCase()}</span>`}</td>
                <td>
                  <div style="font-weight: 700; color: var(--text-primary); font-size: 14px; margin-bottom: 2px;">
                    ${item.title}
                  </div>
                  <div style="font-size: 12px; color: var(--text-muted);">
                    ${item.summary}
                  </div>
                </td>
                <td>
                  <span style="font-size: 12px; color: var(--text-secondary);">
                    ${item.financial_impact || 'Standard'}
                  </span>
                </td>
                <td>
                  <span style="font-size: 12px; font-family: var(--font-mono); color: var(--text-muted);">
                    ${item.deleted_at ? new Date(item.deleted_at).toLocaleString('en-IN') : 'Recently'}
                  </span>
                </td>
                <td>
                  <span style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">
                    ${item.deleted_by}
                  </span>
                </td>
                <td>
                  <span style="font-size: 12px; color: var(--text-muted); font-style: italic;">
                    ${item.deletion_reason || 'Deleted'}
                  </span>
                </td>
                <td style="text-align: right;">
                  <button 
                    class="btn btn-primary btn-sm restore-action-btn"
                    data-entity-type="${item.entity_type}"
                    data-id="${item.id}"
                    data-title="${item.title}"
                    style="padding: 6px 12px; font-size: 12px; font-weight: 700;"
                  >
                    <span>↩️</span> Undo / Restore
                  </button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;

    display.querySelectorAll('.restore-action-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const entityType = btn.getAttribute('data-entity-type');
        const id = btn.getAttribute('data-id');
        const title = btn.getAttribute('data-title');

        btn.disabled = true;
        btn.innerHTML = `<span>⏳</span> Restoring...`;

        try {
          if (entityType === 'deal') await API.restoreDeal(id);
          else if (entityType === 'chain') await API.restoreChain(id);
          else if (entityType === 'party') await API.restoreParty(id);
          else if (entityType === 'product') await API.restoreProduct(id);
          else if (entityType === 'payment') await API.restorePayment(id);

          Store.showToast(`Successfully restored: ${title}`, 'success');
          this.loadData(container);
        } catch (err) {
          Store.showToast(`Failed to restore ${title}: ${err.message}`, 'error');
          btn.disabled = false;
          btn.innerHTML = `<span>↩️</span> Undo / Restore`;
        }
      });
    });
  }
};

window.DeletedItemsComponent = DeletedItemsComponent;
