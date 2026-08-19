/**
 * Comprehensive Reports Suite Component
 */
const ReportsComponent = {
  currentReportType: 'deals',

  async render(container) {
    const parties = Store.state.parties || [];
    const products = Store.state.products || [];

    container.innerHTML = `
      <div class="animate-fade-in">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
          <div>
            <h1>Comprehensive Reports Suite</h1>
            <p class="text-secondary" style="font-size: 0.875rem;">Multi-Parameter Filterable Commodity & Brokerage Registers</p>
          </div>
          <button class="btn btn-primary" onclick="ReportsComponent.downloadExcel()">
            <span>📥</span> Download Excel (.xlsx)
          </button>
        </div>

        <!-- Filter Toolbar -->
        <div class="filter-toolbar">
          <div class="filter-item">
            <label>Report View:</label>
            <select id="rep_type" class="form-select" style="min-width: 220px;" onchange="ReportsComponent.switchReport(this.value)">
              <option value="deals">1. Deal Register (All Deals)</option>
              <option value="price_diff">2. Price-Diff Profit Report</option>
              <option value="buyer_brokerage">3. Buyer Brokerage Report</option>
              <option value="seller_brokerage">4. Seller Brokerage Report</option>
              <option value="earnings">5. Total Earnings Report</option>
              <option value="party_outstanding">6. Party-wise Outstanding</option>
              <option value="pending_deliveries">7. Pending Deliveries</option>
              <option value="cancelled">8. Cancelled Transactions</option>
            </select>
          </div>

          <div class="filter-item">
            <label>From Date:</label>
            <input type="date" id="rep_from_date" class="form-control" style="width: 140px;" onchange="ReportsComponent.loadReport()">
          </div>

          <div class="filter-item">
            <label>To Date:</label>
            <input type="date" id="rep_to_date" class="form-control" style="width: 140px;" onchange="ReportsComponent.loadReport()">
          </div>

          <div class="filter-item">
            <label>Party:</label>
            <select id="rep_party_id" class="form-select" style="max-width: 200px;" onchange="ReportsComponent.loadReport()">
              <option value="">-- All Parties --</option>
              ${parties.map(p => `<option value="${p.id}">${p.name}</option>`).join('')}
            </select>
          </div>

          <div class="filter-item">
            <label>Product:</label>
            <select id="rep_product_id" class="form-select" style="max-width: 160px;" onchange="ReportsComponent.loadReport()">
              <option value="">-- All Products --</option>
              ${products.map(pr => `<option value="${pr.id}">${pr.code}</option>`).join('')}
            </select>
          </div>

          <div class="filter-item" style="margin-left: auto;">
            <button class="btn btn-sm btn-secondary" onclick="ReportsComponent.resetFilters()">
              <span>🔄</span> Reset
            </button>
          </div>
        </div>

        <!-- Report Data Card -->
        <div class="card">
          <div class="card-header">
            <div class="card-title" id="report-heading"><span>📊</span> Report Data Table</div>
            <div id="report-summary-badge" class="font-mono text-gold font-bold"></div>
          </div>

          <div class="table-responsive">
            <table class="data-table" id="report-data-table">
              <thead>
                <!-- Headers rendered dynamically based on report type -->
              </thead>
              <tbody>
                <tr><td colspan="12" style="text-align: center;">Loading report...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    await this.loadReport();
  },

  switchReport(type) {
    this.currentReportType = type;
    this.loadReport();
  },

  resetFilters() {
    document.getElementById('rep_from_date').value = '';
    document.getElementById('rep_to_date').value = '';
    document.getElementById('rep_party_id').value = '';
    document.getElementById('rep_product_id').value = '';
    this.loadReport();
  },

  async loadReport() {
    const params = {
      from_date: document.getElementById('rep_from_date')?.value || '',
      to_date: document.getElementById('rep_to_date')?.value || '',
      party_id: document.getElementById('rep_party_id')?.value || '',
      product_id: document.getElementById('rep_product_id')?.value || ''
    };

    try {
      const res = await API.getReport(this.currentReportType, params);
      if (!res.success) return;

      this.renderTable(res.rows || []);
    } catch (err) {
      Store.showToast('Error loading report: ' + err.message, 'error');
    }
  },

  renderTable(rows) {
    const thead = document.querySelector('#report-data-table thead');
    const tbody = document.querySelector('#report-data-table tbody');
    const badge = document.getElementById('report-summary-badge');

    if (this.currentReportType === 'party_outstanding') {
      thead.innerHTML = `
        <tr>
          <th>Party Name</th>
          <th>Type</th>
          <th>City</th>
          <th>GSTIN</th>
          <th>Total Brokerage Charged</th>
          <th>Total Payments Received</th>
          <th>Net Outstanding Balance</th>
          <th>Communication</th>
        </tr>
      `;

      let totalCharged = 0;
      let totalPaid = 0;
      let totalOut = 0;

      tbody.innerHTML = rows.map(r => {
        totalCharged += r.total_brokerage_charged;
        totalPaid += r.total_brokerage_paid;
        totalOut += r.outstanding_brokerage;

        return `
          <tr>
            <td><strong>${r.name}</strong></td>
            <td><span class="badge badge-info">${r.party_type}</span></td>
            <td>${r.city || 'India'}</td>
            <td class="font-mono">${r.gstin || 'N/A'}</td>
            <td class="font-mono text-gold">${Store.formatINR(r.total_brokerage_charged)}</td>
            <td class="font-mono text-profit">${Store.formatINR(r.total_brokerage_paid)}</td>
            <td class="font-mono font-bold ${r.outstanding_brokerage > 0 ? 'text-gold' : 'text-profit'}">
              ${Store.formatINR(r.outstanding_brokerage)}
            </td>
            <td>
              <div style="display: flex; gap: 4px;">
                <button class="btn btn-sm btn-success" style="font-size: 0.7rem; padding: 2px 6px; background: #22c55e; color: #000;" onclick="CommModalComponent.open({ message_type: 'brokerage_statement', party_id: ${r.id} })" title="Send Brokerage Statement">
                  💬 WhatsApp
                </button>
                <button class="btn btn-sm btn-primary" style="font-size: 0.7rem; padding: 2px 6px;" onclick="CommModalComponent.open({ message_type: 'brokerage_payment_reminder', party_id: ${r.id} })" title="Send Payment Reminder">
                  ✉️ Reminder
                </button>
              </div>
            </td>
          </tr>
        `;
      }).join('');

      badge.innerText = `Total Outstanding: ${Store.formatINR(totalOut)}`;
      return;
    }

    // Standard Deal-based Reports
    thead.innerHTML = `
      <tr>
        <th>Deal Date [Col A]</th>
        <th>Buyer [Col B]</th>
        <th>Seller [Col C]</th>
        <th>Product [Col D]</th>
        <th>Quantity [Col E]</th>
        <th>Price + GST [Col F]</th>
        <th>Delivery [Col G]</th>
        <th>Authorized Rate</th>
        <th>Price Diff Profit</th>
        <th>Buyer Brok</th>
        <th>Seller Brok</th>
        <th>Total Brok</th>
        <th>Total Earning</th>
        <th>Status</th>
        <th>Dispatch</th>
      </tr>
    `;

    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="15" style="text-align: center;">No transaction records found matching filters.</td></tr>';
      badge.innerText = '';
      return;
    }

    let totProfit = 0;
    let totBuyerBrok = 0;
    let totSellerBrok = 0;
    let totBrok = 0;
    let totEarn = 0;

    tbody.innerHTML = rows.map(d => {
      totProfit += Number(d.price_diff_profit || 0);
      totBuyerBrok += Number(d.buyer_brokerage_amount || 0);
      totSellerBrok += Number(d.seller_brokerage_amount || 0);
      totBrok += Number(d.total_brokerage || 0);
      totEarn += Number(d.total_deal_earning || 0);

      const diff = Number(d.price_diff_profit || 0);

      return `
        <tr>
          <td>${Store.formatDate(d.deal_date)}</td>
          <td><strong>${d.buyer_name}</strong></td>
          <td>${d.seller_name}</td>
          <td><span class="badge badge-info">${d.product_code || 'M.OIL'}</span></td>
          <td>${Store.formatQty(d.quantity_qtl)}</td>
          <td class="font-mono">₹${Number(d.rate_per_qtl).toLocaleString('en-IN')}/Qtl ${d.gst_applicable ? '+ GST' : ''}</td>
          <td>${Store.formatDate(d.delivery_date)}</td>
          <td class="font-mono">${d.authorized_rate_per_qtl > 0 ? `₹${d.authorized_rate_per_qtl}` : '-'}</td>
          <td class="font-mono font-bold ${diff > 0 ? 'text-profit' : (diff < 0 ? 'text-loss' : 'text-muted')}">
            ${Store.formatINR(d.price_diff_profit)}
          </td>
          <td class="font-mono">${Store.formatINR(d.buyer_brokerage_amount)}</td>
          <td class="font-mono">${Store.formatINR(d.seller_brokerage_amount)}</td>
          <td class="font-mono text-gold font-bold">${Store.formatINR(d.total_brokerage)}</td>
          <td class="font-mono" style="color: #38bdf8; font-weight: 700;">${Store.formatINR(d.total_deal_earning)}</td>
          <td><span class="badge badge-${d.status}">${d.status}</span></td>
          <td>
            <button class="btn btn-sm btn-secondary" style="font-size: 0.7rem; padding: 2px 6px;" onclick="CommModalComponent.open({ message_type: 'deal_confirmation_buyer', deal_id: ${d.id}, party_id: ${d.buyer_id} })" title="Send Deal Communication">
              💬 Dispatch
            </button>
          </td>
        </tr>
      `;
    }).join('');

    badge.innerText = `Total Net Earnings: ${Store.formatINR(totEarn)} (Profit: ${Store.formatINR(totProfit)} | Brokerage: ${Store.formatINR(totBrok)})`;
  },

  downloadExcel() {
    const params = {
      from_date: document.getElementById('rep_from_date')?.value || '',
      to_date: document.getElementById('rep_to_date')?.value || '',
      party_id: document.getElementById('rep_party_id')?.value || '',
      product_id: document.getElementById('rep_product_id')?.value || ''
    };
    API.downloadExcel(params);
  }
};
