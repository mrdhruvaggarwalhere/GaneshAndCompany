/**
 * Dashboard View Component
 */
const DashboardComponent = {
  async render(container) {
    container.innerHTML = `
      <div class="animate-fade-in">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
          <div>
            <h1>Central Automation Dashboard</h1>
            <p class="text-secondary" style="font-size: 0.875rem;">Live Commodity Deals, Multi-Link Resale Margins & Brokerage Receivables</p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="btn btn-primary" onclick="App.navigate('new_deal')">
              <span>➕</span> New Deal Entry
            </button>
            <button class="btn btn-secondary" onclick="API.downloadExcel()">
              <span>📥</span> Export Register (.xlsx)
            </button>
          </div>
        </div>

        <!-- Metric KPI Cards -->
        <div class="metrics-grid" id="dashboard-metrics">
          <div class="card metric-card profit-theme glow-profit">
            <div class="metric-header">
              <span>Price-Diff Profit</span>
              <span>📈</span>
            </div>
            <div class="metric-value text-profit" id="metric-profit">₹0.00</div>
            <div class="metric-subtext">Cumulative trading margin across resale chains</div>
          </div>

          <div class="card metric-card gold-theme glow-gold">
            <div class="metric-header">
              <span>Total Brokerage</span>
              <span>💼</span>
            </div>
            <div class="metric-value text-gold" id="metric-brokerage">₹0.00</div>
            <div class="metric-subtext">Buyer + Seller Commission (₹/MT)</div>
          </div>

          <div class="card metric-card">
            <div class="metric-header">
              <span>Total Net Earnings</span>
              <span>💰</span>
            </div>
            <div class="metric-value" id="metric-earning">₹0.00</div>
            <div class="metric-subtext">Price-Difference + Total Brokerage</div>
          </div>

          <div class="card metric-card alert-theme">
            <div class="metric-header">
              <span>Pending Deliveries</span>
              <span>🚚</span>
            </div>
            <div class="metric-value" id="metric-deliveries">0 Due</div>
            <div class="metric-subtext" id="metric-overdue" style="color: var(--loss-red);">0 Overdue</div>
          </div>
        </div>

        <!-- Secondary Highlights Row -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 24px;">
          
          <!-- Chain Status Widget -->
          <div class="card">
            <div class="card-header">
              <div class="card-title"><span>⛓️</span> Active Deal Chains Status</div>
              <button class="btn btn-sm btn-secondary" onclick="App.navigate('chains')">View All</button>
            </div>
            <div style="display: flex; gap: 16px; align-items: center; justify-content: space-around; padding: 12px 0;">
              <div style="text-align: center;">
                <div style="font-size: 1.75rem; font-weight: 700; color: var(--warning-amber);" id="metric-chains-progress">0</div>
                <div class="text-muted" style="font-size: 0.75rem;">AWAITING FINAL BUYER</div>
              </div>
              <div style="height: 40px; width: 1px; background: var(--border-subtle);"></div>
              <div style="text-align: center;">
                <div style="font-size: 1.75rem; font-weight: 700; color: var(--profit-green);" id="metric-chains-ready">0</div>
                <div class="text-muted" style="font-size: 0.75rem;">READY FOR DIRECT BILL</div>
              </div>
            </div>
          </div>

          <!-- Top Brokerage Receivables Widget -->
          <div class="card">
            <div class="card-header">
              <div class="card-title"><span>💳</span> Top Party Receivables</div>
              <button class="btn btn-sm btn-secondary" onclick="App.navigate('parties')">Party Ledger</button>
            </div>
            <div id="dashboard-receivables-list" style="display: flex; flex-direction: column; gap: 8px;">
              <div class="text-muted" style="font-size: 0.8125rem;">Loading party receivables...</div>
            </div>
          </div>
        </div>

        <!-- Recent Deals Table -->
        <div class="card">
          <div class="card-header">
            <div class="card-title"><span>📋</span> Recent Transactions & Chains</div>
            <button class="btn btn-sm btn-outline-gold" onclick="App.navigate('reports')">Full Deal Register</button>
          </div>
          <div class="table-responsive">
            <table class="data-table" id="dashboard-recent-deals">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Deal / Chain ID</th>
                  <th>Buyer</th>
                  <th>Seller</th>
                  <th>Product</th>
                  <th>Quantity</th>
                  <th>Rate + GST</th>
                  <th>Price Diff (₹)</th>
                  <th>Total Brokerage</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr><td colspan="11" style="text-align: center;">Loading recent transactions...</td></tr>
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
      const res = await API.getDashboard();
      if (!res.success) return;

      const s = res.summary;
      document.getElementById('metric-profit').innerText = Store.formatINR(s.total_price_diff_profit);
      document.getElementById('metric-brokerage').innerText = Store.formatINR(s.total_brokerage);
      document.getElementById('metric-earning').innerText = Store.formatINR(s.total_earning);
      document.getElementById('metric-deliveries').innerText = `${s.due_today} Today`;
      document.getElementById('metric-overdue').innerText = `${s.overdue_deliveries} Overdue Delivery Alerts`;
      
      document.getElementById('metric-chains-progress').innerText = s.chains_in_progress;
      document.getElementById('metric-chains-ready').innerText = s.chains_ready_billing;

      // Populate Party Receivables
      const recList = document.getElementById('dashboard-receivables-list');
      if (res.party_receivables && res.party_receivables.length > 0) {
        recList.innerHTML = res.party_receivables.map(p => `
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: rgba(0,0,0,0.2); border-radius: var(--radius-sm);">
            <div>
              <div style="font-size: 0.8125rem; font-weight: 600;">${p.name}</div>
              <div class="text-muted" style="font-size: 0.7rem;">${p.city || 'India'}</div>
            </div>
            <div style="text-align: right;">
              <div class="text-gold font-mono" style="font-weight: 700; font-size: 0.875rem;">${Store.formatINR(p.total_charged - p.total_paid)}</div>
              <div class="text-muted" style="font-size: 0.65rem;">OUTSTANDING</div>
            </div>
          </div>
        `).join('');
      } else {
        recList.innerHTML = '<div class="text-muted" style="font-size: 0.8125rem;">All brokerage balances currently settled.</div>';
      }

      // Populate Recent Deals
      const tbody = document.querySelector('#dashboard-recent-deals tbody');
      if (res.recent_deals && res.recent_deals.length > 0) {
        tbody.innerHTML = res.recent_deals.map(d => `
          <tr>
            <td>${Store.formatDate(d.deal_date)}</td>
            <td>
              <a href="#" onclick="App.viewChain(${d.chain_id}); return false;" style="color: var(--info-blue); font-weight: 600; text-decoration: none;">
                ${d.deal_number}
              </a>
              <div class="text-muted" style="font-size: 0.7rem;">${d.chain_code || ''}</div>
            </td>
            <td>
              <strong>${d.buyer_name}</strong>
              ${d.authorized_rate_per_qtl > 0 ? `<span class="badge badge-info" style="font-size: 0.65rem; margin-left: 4px;">Auth @ ₹${d.authorized_rate_per_qtl}/-</span>` : ''}
            </td>
            <td>
              ${d.seller_name}
            </td>
            <td><span class="badge badge-info">${d.product_code || d.product_name}</span></td>
            <td>${Store.formatQty(d.quantity_qtl)}</td>
            <td class="font-mono">₹${Number(d.rate_per_qtl).toLocaleString('en-IN')}/Qtl ${d.gst_applicable ? '+ GST' : ''}</td>
            <td class="font-mono ${d.price_diff_profit > 0 ? 'text-profit' : (d.price_diff_profit < 0 ? 'text-loss' : 'text-muted')}">
              ${Store.formatINR(d.price_diff_profit)}
            </td>
            <td class="font-mono text-gold">${Store.formatINR(d.total_brokerage)}</td>
            <td><span class="badge badge-${d.status}">${d.status}</span></td>
            <td>
              <div style="display: flex; flex-direction: row; flex-wrap: nowrap; gap: 6px; align-items: center; white-space: nowrap;">
                <button class="btn btn-sm btn-glass-success" style="padding: 4px 8px; font-size: 11px;" onclick="CommModalComponent.open({ message_type: 'deal_confirmation_buyer', deal_id: ${d.id}, party_id: ${d.buyer_id} })" title="Send WhatsApp / Email confirmation">
                  💬
                </button>
                <button class="btn btn-sm btn-glass-primary" style="padding: 4px 8px; font-size: 11px;" onclick="App.viewChain(${d.chain_id})">
                  Chain
                </button>
                <button 
                  class="btn btn-sm btn-glass-default" 
                  title="Delete Deal"
                  style="padding: 4px 8px; font-size: 11px; color: var(--danger-red);"
                  onclick="DashboardComponent.deleteDeal(${d.id}, '${d.deal_number}')"
                >
                  🗑️
                </button>
              </div>
            </td>
          </tr>
        `).join('');
      } else {
        tbody.innerHTML = '<tr><td colspan="11" style="text-align: center; color: var(--text-muted); padding: 32px 16px;"><span>✨</span> No unbilled active deals. Approved commercial billing transactions are archived in the <a href="#" onclick="App.navigate(\'reports\'); return false;" style="color: var(--text-gold); font-weight: 600;">Full Deal Register</a> or <a href="#" onclick="App.navigate(\'chains\'); return false;" style="color: var(--info-blue); font-weight: 600;">Deal Chains</a>.</td></tr>';
      }

    } catch (err) {
      Store.showToast('Error loading dashboard: ' + err.message, 'error');
    }
  },

  async deleteDeal(dealId, dealNumber) {
    if (!confirm(`Are you sure you want to delete Deal ${dealNumber}?\n\nIt will be moved to the Deleted Items recycle bin, and you can undo/restore it anytime.`)) {
      return;
    }

    try {
      await API.deleteDeal(dealId, 'Deleted from dashboard table');
      
      Store.showToast(`Deal ${dealNumber} deleted.`, 'warning', async () => {
        await API.restoreDeal(dealId);
        Store.showToast(`Deal ${dealNumber} restored successfully!`, 'success');
        DashboardComponent.loadData();
      });

      this.loadData();
    } catch (err) {
      Store.showToast(`Failed to delete deal: ${err.message}`, 'error');
    }
  }
};
