/**
 * Party Master & Brokerage Ledger Statement Component
 */
const PartyLedgerComponent = {
  activePartyId: null,
  isSidebarOpen: true,

  async render(container, partyId) {
    this.activePartyId = partyId || Store.state.activePartyId || null;

    container.innerHTML = `
      <div class="animate-fade-in">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
          <div>
            <h1>Party Master & Brokerage Statement</h1>
            <p class="text-secondary" style="font-size: 0.875rem;">Manage Client Masters, Dual Brokerage Defaults, and Detailed Transaction Statements</p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button id="toggle-sidebar-btn" class="btn btn-secondary" onclick="PartyLedgerComponent.toggleSidebar()" title="Toggle Parties Directory Sidebar">
              <span>⬅️</span>
            </button>
            <button class="btn btn-primary" onclick="PartyLedgerComponent.openAddPartyModal()">
              <span>➕</span> Add New Party
            </button>
            <button class="btn btn-secondary" onclick="API.downloadExcel()">
              <span>📥</span> Export Party Ledgers (.xlsx)
            </button>
          </div>
        </div>

        <div id="party-ledger-grid" style="display: grid; grid-template-columns: minmax(280px, 1fr) 2fr; gap: 24px; align-items: start;">
          
          <!-- Left: Party Directory List -->
          <div id="party-sidebar" class="card" style="min-height: 400px; max-height: calc(100vh - 200px); display: flex; flex-direction: column; position: sticky; top: 80px;">
            <div class="card-header" style="margin-bottom: 12px;">
              <div class="card-title"><span>👥</span> Parties Directory</div>
            </div>
            
            <div style="margin-bottom: 12px;">
              <input type="text" id="party-search-input" class="form-control" placeholder="🔍 Search by party name or city..." oninput="PartyLedgerComponent.filterParties(this.value)">
            </div>

            <div id="parties-list-container" style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
              <div class="text-muted">Loading parties...</div>
            </div>
          </div>

          <!-- Right: Individual Party Ledger & Brokerage Statement -->
          <div id="party-statement-container">
            <div class="card" style="text-align: center; padding: 40px;">
              <div style="font-size: 2rem; margin-bottom: 12px;">📑</div>
              <h3>Select a Party to View Brokerage Ledger</h3>
              <p class="text-secondary" style="font-size: 0.875rem; margin-top: 6px;">
                Choose any buying or selling client from the directory on the left to inspect deal records, brokerage commission charges, payment receipts, and balance statements.
              </p>
            </div>
          </div>
        </div>
      </div>
    `;

    await this.loadParties();
    if (this.activePartyId) {
      this.viewPartyStatement(this.activePartyId);
    }
    
    // Maintain state if re-rendered
    if (!this.isSidebarOpen) {
      this.isSidebarOpen = true; // force toggle to close it
      this.toggleSidebar();
    }
  },

  toggleSidebar() {
    this.isSidebarOpen = !this.isSidebarOpen;
    const grid = document.getElementById('party-ledger-grid');
    const sidebar = document.getElementById('party-sidebar');
    const btn = document.getElementById('toggle-sidebar-btn');
    
    if (grid && sidebar && btn) {
      if (this.isSidebarOpen) {
        grid.style.gridTemplateColumns = 'minmax(280px, 1fr) 2fr';
        sidebar.style.display = 'flex';
        btn.innerHTML = '<span>⬅️</span>';
      } else {
        grid.style.gridTemplateColumns = '1fr';
        sidebar.style.display = 'none';
        btn.innerHTML = '<span>➡️</span> Directory';
      }
    }
  },

  async loadParties() {
    try {
      const res = await API.getParties();
      if (!res.success) return;

      Store.setParties(res.parties);
      this.renderPartiesList(res.parties);
    } catch (err) {
      Store.showToast('Error loading parties: ' + err.message, 'error');
    }
  },

  renderPartiesList(parties) {
    const container = document.getElementById('parties-list-container');
    if (!container) return;

    if (parties.length === 0) {
      container.innerHTML = '<div class="text-muted">No parties matching criteria.</div>';
      return;
    }

    container.innerHTML = parties.map(p => {
      const isSelected = p.id === this.activePartyId;
      const outstanding = Number(p.outstanding_brokerage || 0);
      const chainProfit = Number(p.total_chain_profit || 0);
      const dealsCount = Number(p.total_deals_count || 0);

      return `
        <div onclick="PartyLedgerComponent.viewPartyStatement(${p.id})" style="
          padding: 12px 14px;
          border-radius: var(--radius-md);
          background: ${isSelected ? 'rgba(245, 158, 11, 0.15)' : 'rgba(0, 0, 0, 0.2)'};
          border: 1px solid ${isSelected ? 'var(--accent-gold)' : 'var(--border-subtle)'};
          cursor: pointer;
          transition: all var(--transition-fast);
        ">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div style="font-weight: 600; font-size: 0.875rem; color: ${isSelected ? 'var(--text-gold)' : 'var(--text-primary)'};">
              ${p.name}
            </div>
            <div style="display: flex; gap: 4px; align-items: center;">
              <span class="badge badge-${p.party_type === 'both' ? 'info' : 'draft'}" style="font-size: 0.65rem;">
                ${p.party_type}
              </span>
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; font-size: 0.75rem;">
            <span class="text-muted">${p.city || 'India'} | <strong>${dealsCount} record(s)</strong></span>
            <div style="display: flex; flex-direction: column; align-items: flex-end;">
              <span class="font-mono font-bold ${outstanding > 0 ? 'text-gold' : 'text-profit'}">
                Due: ${Store.formatINR(outstanding)}
              </span>
              ${chainProfit > 0 ? `
                <span class="font-mono text-profit" style="font-size: 0.7rem; font-weight: 700;">
                  +${Store.formatINR(chainProfit)} Profit
                </span>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');
  },

  filterParties(query) {
    const q = (query || '').toLowerCase().trim();
    const filtered = (Store.state.parties || []).filter(p => 
      p.name.toLowerCase().includes(q) || (p.city && p.city.toLowerCase().includes(q))
    );
    this.renderPartiesList(filtered);
  },

  async viewPartyStatement(partyId) {
    this.activePartyId = partyId;
    this.renderPartiesList(Store.state.parties || []);

    const container = document.getElementById('party-statement-container');
    container.innerHTML = '<div class="card text-muted">Loading party statement...</div>';

    try {
      const res = await API.getPartyLedger(partyId);
      if (!res.success) return;

      const p = res.party;
      const deals = res.deals || [];
      const payments = res.payments || [];
      const s = res.summary;

      container.innerHTML = `
        <div class="card animate-fade-in">
          
          <!-- Header Profile -->
          <div style="display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 16px; border-bottom: 1px solid var(--border-subtle); margin-bottom: 18px;">
            <div>
              <div style="display: flex; align-items: center; gap: 10px;">
                <h2>${p.name}</h2>
                <span class="badge badge-info">${p.party_type}</span>
              </div>
              <div class="text-secondary" style="font-size: 0.8125rem; margin-top: 4px;">
                ${p.city || ''}, ${p.state || 'India'} | GSTIN: <strong>${p.gstin || 'Unregistered'}</strong> | Contact: ${p.contact_person || 'N/A'} (${p.phone || 'N/A'})
              </div>
              <div class="text-muted" style="font-size: 0.75rem; margin-top: 2px;">
                Default Brokerage: Buyer ₹${p.default_buyer_brokerage_rate}/MT, Seller ₹${p.default_seller_brokerage_rate}/MT | BUSY Ledger: <code>${p.busy_ledger_id || 'UNMAPPED'}</code>
              </div>
            </div>
            
            <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
              <div style="display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end;">
                <button class="btn btn-sm btn-success" style="background: #22c55e; color: #000; font-weight: 700;" onclick="CommModalComponent.open({ message_type: 'brokerage_statement', party_id: ${p.id} })">
                  <span>💬</span> WhatsApp
                </button>
                <button class="btn btn-sm btn-primary" onclick="CommModalComponent.open({ message_type: 'brokerage_statement', party_id: ${p.id} })">
                  <span>✉️</span> Email
                </button>
                <button class="btn btn-sm btn-warning" style="background: rgba(245, 158, 11, 0.2); color: var(--text-gold); border: 1px solid var(--text-gold);" onclick="CommModalComponent.open({ message_type: 'brokerage_payment_reminder', party_id: ${p.id} })">
                  <span>💵</span> Payment Reminder
                </button>
                <button class="btn btn-sm btn-secondary" onclick="CommModalComponent.open({ message_type: 'custom_message', party_id: ${p.id} })">
                  <span>📝</span> Custom Note
                </button>
              </div>

              <div style="display: flex; gap: 6px;">
                <button class="btn btn-sm btn-secondary" onclick="PartyLedgerComponent.openEditPartyModal(${p.id})">
                  <span>✏️</span> Edit Master
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="PartyLedgerComponent.deleteParty(${p.id}, '${p.name}')" style="border-color: rgba(239, 68, 68, 0.4); color: var(--danger-red);">
                  <span>🗑️</span> Delete
                </button>
                <button class="btn btn-sm btn-primary" onclick="PartyLedgerComponent.openRecordPaymentModal(${p.id}, '${p.name}')">
                  <span>💳</span> Record Payment
                </button>
              </div>
            </div>
          </div>

          <!-- Statement Financial Summary Cards (Brokerage + Chain Profit) -->
          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;">
            <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: var(--radius-md); border-left: 3px solid var(--text-gold);">
              <div class="text-muted" style="font-size: 0.75rem; text-transform: uppercase;">Total Brokerage Billed</div>
              <div class="font-mono text-gold" style="font-size: 1.2rem; font-weight: 700; margin-top: 4px;">
                ${Store.formatINR(s.total_brokerage_charged)}
              </div>
              <div class="text-muted" style="font-size: 0.7rem;">Across ${s.total_deals} transaction(s)</div>
            </div>

            <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: var(--radius-md); border-left: 3px solid #22c55e;">
              <div class="text-muted" style="font-size: 0.75rem; text-transform: uppercase;">Chain Margin Profit</div>
              <div class="font-mono text-profit" style="font-size: 1.2rem; font-weight: 700; margin-top: 4px;">
                +${Store.formatINR(s.total_chain_profit || 0)}
              </div>
              <div class="text-muted" style="font-size: 0.7rem;">Price difference realized</div>
            </div>

            <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: var(--radius-md); border-left: 3px solid var(--info-blue);">
              <div class="text-muted" style="font-size: 0.75rem; text-transform: uppercase;">Brokerage Received</div>
              <div class="font-mono" style="color: #38bdf8; font-size: 1.2rem; font-weight: 700; margin-top: 4px;">
                ${Store.formatINR(s.total_brokerage_paid)}
              </div>
              <div class="text-muted" style="font-size: 0.7rem;">Settled via receipts</div>
            </div>

            <div style="background: rgba(0,0,0,0.25); padding: 14px; border-radius: var(--radius-md); border-left: 3px solid ${s.outstanding_balance > 0 ? 'var(--accent-gold)' : 'var(--profit-green)'};">
              <div class="text-muted" style="font-size: 0.75rem; text-transform: uppercase;">Net Due Balance</div>
              <div class="font-mono" style="font-size: 1.2rem; font-weight: 700; color: ${s.outstanding_balance > 0 ? 'var(--accent-gold)' : 'var(--profit-green)'}; margin-top: 4px;">
                ${Store.formatINR(s.outstanding_balance)}
              </div>
              <div class="text-muted" style="font-size: 0.7rem;">${s.outstanding_balance > 0 ? 'Brokerage pending' : 'Account in clear'}</div>
            </div>
          </div>

          <!-- Transaction Deal List with Chain Profit Column -->
          <div class="card-title" style="font-size: 0.95rem; margin-bottom: 12px;"><span>📋</span> Associated Records & Brokerage Transactions (${deals.length} records)</div>
          <div class="table-responsive" style="margin-bottom: 24px;">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Deal No</th>
                  <th>Chain Code</th>
                  <th>Role</th>
                  <th>Counterparty</th>
                  <th>Product</th>
                  <th>Quantity</th>
                  <th>Rate/Qtl</th>
                  <th>Chain Margin Profit</th>
                  <th>Brokerage Charged</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${deals.length > 0 ? deals.map(d => {
                  const profit = Number(d.price_diff_profit || 0);
                  return `
                    <tr>
                      <td>${Store.formatDate(d.deal_date)}</td>
                      <td><a href="#" onclick="App.viewChain(${d.chain_id}); return false;" style="color: var(--info-blue); font-weight: 600;">${d.deal_number}</a></td>
                      <td><span class="text-muted font-mono" style="font-size: 0.75rem;">${d.chain_code || '-'}</span></td>
                      <td><span class="badge badge-${d.party_role === 'BUYER' ? 'info' : 'ready'}">${d.party_role}</span></td>
                      <td><strong>${d.party_role === 'BUYER' ? d.seller_name : d.buyer_name}</strong></td>
                      <td><span class="badge badge-info">${d.product_code}</span></td>
                      <td>${Store.formatQty(d.quantity_qtl)}</td>
                      <td class="font-mono">₹${Number(d.rate_per_qtl).toLocaleString('en-IN')}</td>
                      <td class="font-mono ${profit > 0 ? 'text-profit font-bold' : 'text-muted'}">
                        ${profit > 0 ? `+${Store.formatINR(profit)}` : '-'}
                      </td>
                      <td class="font-mono text-gold font-bold">${Store.formatINR(d.party_brokerage)}</td>
                      <td><span class="badge badge-${d.status}">${d.status}</span></td>
                    </tr>
                  `;
                }).join('') : '<tr><td colspan="11" style="text-align: center;">No deal records found for this party.</td></tr>'}
              </tbody>
            </table>
          </div>

          <!-- Payments & Receipts History -->
          <div class="card-title" style="font-size: 0.95rem; margin-bottom: 12px;"><span>💵</span> Payment & Adjustment Receipts</div>
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Receipt Date</th>
                  <th>Type</th>
                  <th>Amount</th>
                  <th>Reference / UTR</th>
                  <th>Mode</th>
                  <th>Notes</th>
                  <th style="width: 80px; text-align: right;">Action</th>
                </tr>
              </thead>
              <tbody>
                ${payments.length > 0 ? payments.map(pm => `
                  <tr>
                    <td>${Store.formatDate(pm.payment_date)}</td>
                    <td><span class="badge badge-profit">${pm.payment_type}</span></td>
                    <td class="font-mono text-profit font-bold">${Store.formatINR(pm.amount)}</td>
                    <td class="font-mono">${pm.reference_number || 'N/A'}</td>
                    <td>${pm.bank_or_mode || 'Bank Transfer'}</td>
                    <td>${pm.notes || '-'}</td>
                    <td style="text-align: right;">
                      <button 
                        class="btn btn-sm btn-outline-danger" 
                        title="Delete Payment"
                        style="padding: 2px 6px; font-size: 11px; border-color: rgba(239, 68, 68, 0.4); color: var(--danger-red);"
                        onclick="PartyLedgerComponent.deletePayment(${pm.id}, ${p.id})"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                `).join('') : '<tr><td colspan="7" style="text-align: center;">No payment entries recorded yet.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
      `;

    } catch (err) {
      container.innerHTML = `<div class="card text-loss">Error: ${err.message}</div>`;
    }
  },

  async deleteParty(partyId, partyName) {
    if (!confirm(`Are you sure you want to delete Party "${partyName}"?\n\nIt will be moved to Deleted Items where you can restore it anytime.`)) {
      return;
    }

    try {
      await API.deleteParty(partyId, 'Deleted from party ledger');
      Store.showToast(`Party "${partyName}" deleted.`, 'warning', async () => {
        await API.restoreParty(partyId);
        Store.showToast(`Party "${partyName}" restored successfully!`, 'success');
        PartyLedgerComponent.loadParties();
        PartyLedgerComponent.viewPartyStatement(partyId);
      });
      this.activePartyId = null;
      this.loadParties();
      document.getElementById('party-statement-container').innerHTML = '<div class="card text-muted">Select a party from the directory to inspect account statement.</div>';
    } catch (err) {
      Store.showToast(`Delete party failed: ${err.message}`, 'error');
    }
  },

  async deletePayment(paymentId, partyId) {
    if (!confirm(`Are you sure you want to delete payment receipt #${paymentId}?\n\nIt will be moved to Deleted Items where you can restore it anytime.`)) {
      return;
    }

    try {
      await API.deletePayment(paymentId, 'Deleted from payment receipts table');
      Store.showToast(`Payment receipt #${paymentId} deleted.`, 'warning', async () => {
        await API.restorePayment(paymentId);
        Store.showToast(`Payment receipt #${paymentId} restored!`, 'success');
        PartyLedgerComponent.viewPartyStatement(partyId);
      });
      this.viewPartyStatement(partyId);
    } catch (err) {
      Store.showToast(`Delete payment failed: ${err.message}`, 'error');
    }
  },

  openAddPartyModal() {
    const bodyHtml = `
      <form id="party-modal-form" onsubmit="PartyLedgerComponent.handleAddPartySubmit(event)">
        <div class="form-group">
          <label class="form-label">Legal / Trade Name *</label>
          <input type="text" id="p_name" class="form-control" placeholder="e.g. HARYANA INDUSTRIES, PANCHKULA" required>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Party Role *</label>
            <select id="p_type" class="form-select" required>
              <option value="both">Both (Buyer & Seller)</option>
              <option value="buyer">Buyer Only</option>
              <option value="seller">Seller Only</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">GSTIN (Optional)</label>
            <input type="text" id="p_gstin" class="form-control" placeholder="e.g. 06AAACH1111A1Z5">
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">City *</label>
            <input type="text" id="p_city" class="form-control" placeholder="e.g. Panchkula" required>
          </div>
          <div class="form-group">
            <label class="form-label">State *</label>
            <input type="text" id="p_state" class="form-control" placeholder="e.g. Haryana" required>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Default Buyer Brokerage (₹/MT)</label>
            <input type="number" step="0.01" id="p_buyer_brok" class="form-control font-mono" value="50.0">
          </div>
          <div class="form-group">
            <label class="form-label">Default Seller Brokerage (₹/MT)</label>
            <input type="number" step="0.01" id="p_seller_brok" class="form-control font-mono" value="50.0">
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Contact Person</label>
            <input type="text" id="p_contact" class="form-control" placeholder="e.g. Rajesh Kumar">
          </div>
          <div class="form-group">
            <label class="form-label">Preferred Communication Method</label>
            <select id="p_pref_comm" class="form-select">
              <option value="both">Both (WhatsApp & Email)</option>
              <option value="whatsapp">WhatsApp Only</option>
              <option value="email">Email Only</option>
            </select>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Preferred Language</label>
            <select id="p_pref_lang" class="form-select">
              <option value="english">English</option>
              <option value="hindi">Hindi</option>
              <option value="bilingual">Bilingual (English + Hindi)</option>
            </select>
          </div>
          <div class="form-group" style="display: flex; align-items: center; gap: 16px; margin-top: 24px;">
            <label style="display: flex; align-items: center; gap: 6px; font-size: 0.75rem; cursor: pointer;">
              <input type="checkbox" id="p_wa_enabled" checked>
              <span>WhatsApp Enabled</span>
            </label>
            <label style="display: flex; align-items: center; gap: 6px; font-size: 0.75rem; cursor: pointer;">
              <input type="checkbox" id="p_em_enabled" checked>
              <span>Email Enabled</span>
            </label>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; background: rgba(0,0,0,0.15); padding: 10px; border-radius: var(--radius-sm); margin-bottom: 12px;">
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.75rem;">📱 WhatsApp Primary (91...)</label>
            <input type="text" id="p_wa_primary" class="form-control font-mono" placeholder="919876543210">
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.75rem;">📱 WhatsApp Secondary (Optional)</label>
            <input type="text" id="p_wa_secondary" class="form-control font-mono" placeholder="919812000000">
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; background: rgba(0,0,0,0.15); padding: 10px; border-radius: var(--radius-sm); margin-bottom: 12px;">
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.75rem;">✉️ Primary Email Address</label>
            <input type="email" id="p_em_primary" class="form-control" placeholder="trading@example.com">
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.75rem;">✉️ Secondary / Accounts Email (Optional)</label>
            <input type="email" id="p_em_secondary" class="form-control" placeholder="accounts@example.com">
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Communication Consent Notes</label>
          <input type="text" id="p_consent_notes" class="form-control" placeholder="e.g. Authorized communication via WhatsApp and Rediffmail">
        </div>

        <div class="form-group">
          <label class="form-label">BUSY Ledger Identifier (Optional)</label>
          <input type="text" id="p_busy" class="form-control" placeholder="e.g. BUSY_HAR_01">
        </div>
      </form>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="Store.closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="document.getElementById('party-modal-form').requestSubmit()">
        <span>💾</span> Save Party Master
      </button>
    `;

    Store.openModal('Add New Party Master', bodyHtml, footerHtml);
  },

  async handleAddPartySubmit(event) {
    event.preventDefault();
    const payload = {
      name: document.getElementById('p_name').value,
      party_type: document.getElementById('p_type').value,
      gstin: document.getElementById('p_gstin').value,
      city: document.getElementById('p_city').value,
      state: document.getElementById('p_state').value,
      default_buyer_brokerage_rate: Number(document.getElementById('p_buyer_brok').value),
      default_seller_brokerage_rate: Number(document.getElementById('p_seller_brok').value),
      contact_person: document.getElementById('p_contact').value,
      preferred_comm_method: document.getElementById('p_pref_comm').value,
      preferred_language: document.getElementById('p_pref_lang').value,
      whatsapp_enabled: document.getElementById('p_wa_enabled').checked,
      email_enabled: document.getElementById('p_em_enabled').checked,
      comm_consent_notes: document.getElementById('p_consent_notes').value,
      whatsapp_primary: document.getElementById('p_wa_primary').value,
      whatsapp_secondary: document.getElementById('p_wa_secondary').value,
      email_primary: document.getElementById('p_em_primary').value,
      email_secondary: document.getElementById('p_em_secondary').value,
      phone: document.getElementById('p_wa_primary').value,
      email: document.getElementById('p_em_primary').value,
      busy_ledger_id: document.getElementById('p_busy').value
    };

    try {
      const res = await API.createParty(payload);
      if (res.success) {
        Store.closeModal();
        Store.showToast('Party master created successfully!', 'success');
        this.loadParties();
      }
    } catch (err) {
      Store.showToast('Failed to create party: ' + err.message, 'error');
    }
  },

  openEditPartyModal(partyId) {
    const party = (Store.state.parties || []).find(p => p.id === partyId);
    if (!party) return;

    const bodyHtml = `
      <form id="edit-party-modal-form" onsubmit="PartyLedgerComponent.handleEditPartySubmit(event, ${partyId})">
        <div class="form-group">
          <label class="form-label">Legal / Trade Name *</label>
          <input type="text" id="ep_name" class="form-control" value="${party.name}" required>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Party Role *</label>
            <select id="ep_type" class="form-select" required>
              <option value="both" ${party.party_type === 'both' ? 'selected' : ''}>Both (Buyer & Seller)</option>
              <option value="buyer" ${party.party_type === 'buyer' ? 'selected' : ''}>Buyer Only</option>
              <option value="seller" ${party.party_type === 'seller' ? 'selected' : ''}>Seller Only</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">GSTIN (Optional)</label>
            <input type="text" id="ep_gstin" class="form-control" value="${party.gstin || ''}">
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">City *</label>
            <input type="text" id="ep_city" class="form-control" value="${party.city || ''}" required>
          </div>
          <div class="form-group">
            <label class="form-label">State *</label>
            <input type="text" id="ep_state" class="form-control" value="${party.state || ''}" required>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Default Buyer Brokerage (₹/MT)</label>
            <input type="number" step="0.01" id="ep_buyer_brok" class="form-control font-mono" value="${party.default_buyer_brokerage_rate || 50.0}">
          </div>
          <div class="form-group">
            <label class="form-label">Default Seller Brokerage (₹/MT)</label>
            <input type="number" step="0.01" id="ep_seller_brok" class="form-control font-mono" value="${party.default_seller_brokerage_rate || 50.0}">
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Contact Person</label>
            <input type="text" id="ep_contact" class="form-control" value="${party.contact_person || ''}" placeholder="e.g. Rajesh Kumar">
          </div>
          <div class="form-group">
            <label class="form-label">Preferred Communication</label>
            <select id="ep_pref_comm" class="form-select">
              <option value="both" ${party.preferred_comm_method === 'both' ? 'selected' : ''}>Both (WhatsApp & Email)</option>
              <option value="whatsapp" ${party.preferred_comm_method === 'whatsapp' ? 'selected' : ''}>WhatsApp Only</option>
              <option value="email" ${party.preferred_comm_method === 'email' ? 'selected' : ''}>Email Only</option>
            </select>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Preferred Language</label>
            <select id="ep_pref_lang" class="form-select">
              <option value="english" ${party.preferred_language === 'english' ? 'selected' : ''}>English</option>
              <option value="hindi" ${party.preferred_language === 'hindi' ? 'selected' : ''}>Hindi</option>
              <option value="bilingual" ${party.preferred_language === 'bilingual' ? 'selected' : ''}>Bilingual (English + Hindi)</option>
            </select>
          </div>
          <div class="form-group" style="display: flex; align-items: center; gap: 16px; margin-top: 24px;">
            <label style="display: flex; align-items: center; gap: 6px; font-size: 0.75rem; cursor: pointer;">
              <input type="checkbox" id="ep_wa_enabled" ${party.whatsapp_enabled !== 0 ? 'checked' : ''}>
              <span>WhatsApp Enabled</span>
            </label>
            <label style="display: flex; align-items: center; gap: 6px; font-size: 0.75rem; cursor: pointer;">
              <input type="checkbox" id="ep_em_enabled" ${party.email_enabled !== 0 ? 'checked' : ''}>
              <span>Email Enabled</span>
            </label>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; background: rgba(0,0,0,0.15); padding: 10px; border-radius: var(--radius-sm); margin-bottom: 12px;">
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.75rem;">📱 WhatsApp Primary (91...)</label>
            <input type="text" id="ep_wa_primary" class="form-control font-mono" value="${party.whatsapp_primary || party.phone || ''}">
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.75rem;">📱 WhatsApp Secondary (Optional)</label>
            <input type="text" id="ep_wa_secondary" class="form-control font-mono" value="${party.whatsapp_secondary || ''}">
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; background: rgba(0,0,0,0.15); padding: 10px; border-radius: var(--radius-sm); margin-bottom: 12px;">
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.75rem;">✉️ Primary Email Address</label>
            <input type="email" id="ep_em_primary" class="form-control" value="${party.email_primary || party.email || ''}">
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.75rem;">✉️ Secondary / Accounts Email (Optional)</label>
            <input type="email" id="ep_em_secondary" class="form-control" value="${party.email_secondary || ''}">
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Communication Consent Notes</label>
          <input type="text" id="ep_consent_notes" class="form-control" value="${party.comm_consent_notes || ''}" placeholder="e.g. Authorized communication via WhatsApp and Rediffmail">
        </div>

        <div class="form-group">
          <label class="form-label">BUSY Ledger ID</label>
          <input type="text" id="ep_busy" class="form-control" value="${party.busy_ledger_id || ''}">
        </div>

        ${party.last_whatsapp_date || party.last_email_date ? `
          <div style="font-size: 0.7rem; color: var(--text-muted); background: rgba(0,0,0,0.2); padding: 8px; border-radius: var(--radius-sm);">
            ${party.last_whatsapp_date ? `<div>📱 Last WhatsApp: ${party.last_whatsapp_date}</div>` : ''}
            ${party.last_email_date ? `<div>✉️ Last Email: ${party.last_email_date}</div>` : ''}
          </div>
        ` : ''}
      </form>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="Store.closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="document.getElementById('edit-party-modal-form').requestSubmit()">
        <span>💾</span> Update Master
      </button>
    `;

    Store.openModal(`Edit Party: ${party.name}`, bodyHtml, footerHtml);
  },

  async handleEditPartySubmit(event, partyId) {
    event.preventDefault();
    const payload = {
      name: document.getElementById('ep_name').value,
      party_type: document.getElementById('ep_type').value,
      gstin: document.getElementById('ep_gstin').value,
      city: document.getElementById('ep_city').value,
      state: document.getElementById('ep_state').value,
      default_buyer_brokerage_rate: Number(document.getElementById('ep_buyer_brok').value),
      default_seller_brokerage_rate: Number(document.getElementById('ep_seller_brok').value),
      contact_person: document.getElementById('ep_contact').value,
      preferred_comm_method: document.getElementById('ep_pref_comm').value,
      preferred_language: document.getElementById('ep_pref_lang').value,
      whatsapp_enabled: document.getElementById('ep_wa_enabled').checked,
      email_enabled: document.getElementById('ep_em_enabled').checked,
      comm_consent_notes: document.getElementById('ep_consent_notes').value,
      whatsapp_primary: document.getElementById('ep_wa_primary').value,
      whatsapp_secondary: document.getElementById('ep_wa_secondary').value,
      email_primary: document.getElementById('ep_em_primary').value,
      email_secondary: document.getElementById('ep_em_secondary').value,
      phone: document.getElementById('ep_wa_primary').value,
      email: document.getElementById('ep_em_primary').value,
      busy_ledger_id: document.getElementById('ep_busy').value
    };

    try {
      const res = await API.updateParty(partyId, payload);
      if (res.success) {
        Store.closeModal();
        Store.showToast('Party master updated!', 'success');
        this.loadParties();
        this.viewPartyStatement(partyId);
      }
    } catch (err) {
      Store.showToast('Failed to update party: ' + err.message, 'error');
    }
  },

  openRecordPaymentModal(partyId, partyName) {
    const today = new Date().toISOString().slice(0, 10);
    const bodyHtml = `
      <form id="payment-modal-form" onsubmit="PartyLedgerComponent.handlePaymentSubmit(event, ${partyId})">
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 12px; border-radius: var(--radius-md); margin-bottom: 16px;">
          <strong>Party: ${partyName}</strong>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Payment Date *</label>
            <input type="date" id="pay_date" class="form-control" value="${today}" required>
          </div>
          <div class="form-group">
            <label class="form-label">Amount Received (₹) *</label>
            <input type="number" step="0.01" id="pay_amount" class="form-control font-mono" placeholder="e.g. 1600" required>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Payment Type</label>
            <select id="pay_type" class="form-select">
              <option value="receipt">Brokerage Receipt</option>
              <option value="adjustment">Settlement Adjustment</option>
              <option value="discount">Authorized Discount</option>
              <option value="tds_deduction">TDS Deduction (Sec 194H)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Payment Mode</label>
            <select id="pay_mode" class="form-select">
              <option value="NEFT / RTGS">NEFT / RTGS</option>
              <option value="UPI / IMPS">UPI / IMPS</option>
              <option value="Cheque">Cheque</option>
              <option value="Internal Adjustment">Internal Adjustment</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Bank Reference / UTR Number</label>
          <input type="text" id="pay_ref" class="form-control" placeholder="e.g. UTR123456789">
        </div>

        <div class="form-group">
          <label class="form-label">Notes & Remarks</label>
          <input type="text" id="pay_notes" class="form-control" placeholder="e.g. Settled against July brokerage bills">
        </div>
      </form>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="Store.closeModal()">Cancel</button>
      <button class="btn btn-success" onclick="document.getElementById('payment-modal-form').requestSubmit()">
        <span>💵</span> Record Receipt
      </button>
    `;

    Store.openModal(`Record Brokerage Receipt (${partyName})`, bodyHtml, footerHtml);
  },

  async handlePaymentSubmit(event, partyId) {
    event.preventDefault();
    const payload = {
      payment_date: document.getElementById('pay_date').value,
      amount: Number(document.getElementById('pay_amount').value),
      payment_type: document.getElementById('pay_type').value,
      bank_or_mode: document.getElementById('pay_mode').value,
      reference_number: document.getElementById('pay_ref').value,
      notes: document.getElementById('pay_notes').value
    };

    try {
      const res = await API.recordPartyPayment(partyId, payload);
      if (res.success) {
        Store.closeModal();
        Store.showToast('Brokerage payment receipt recorded successfully!', 'success');
        this.viewPartyStatement(partyId);
        this.loadParties();
      }
    } catch (err) {
      Store.showToast('Failed to record payment: ' + err.message, 'error');
    }
  }
};
