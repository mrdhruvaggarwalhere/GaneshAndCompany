/**
 * G&C Central Deal and Brokerage Automation Platform
 * Main Application Orchestrator & Router
 */
const App = {
  async init() {
    console.log("Initializing G&C Automation Platform...");
    
    // Bind Store subscriber for role updates
    Store.subscribe((state) => {
      this.updateUserUI(state.currentUser);
    });

    // Load Initial Master Data
    await this.loadInitialData();

    // Attach global keyboard shortcuts
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        this.navigate('new_deal');
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
        e.preventDefault();
        this.navigate('dashboard');
      }
    });

    // Initial Route
    this.navigate('dashboard');
  },

  async loadInitialData() {
    try {
      const [partiesRes, prodsRes, userRes] = await Promise.all([
        API.getParties(),
        API.getProducts(),
        API.getMe()
      ]);

      if (partiesRes.success) Store.setParties(partiesRes.parties);
      if (prodsRes.success) Store.setProducts(prodsRes.products);
      if (userRes.success && userRes.user) Store.setUser(userRes.user);

    } catch (err) {
      console.warn("Could not load initial master data:", err);
    }
  },

  navigate(tab, params = {}) {
    Store.setTab(tab);
    
    // Update active nav link
    document.querySelectorAll('.nav-item a').forEach(el => {
      el.classList.toggle('active', el.dataset.tab === tab);
    });

    const mainContainer = document.getElementById('view-container');
    if (!mainContainer) return;

    window.scrollTo({ top: 0, behavior: 'smooth' });

    switch (tab) {
      case 'dashboard':
        DashboardComponent.render(mainContainer);
        break;
      case 'new_deal':
        DealFormComponent.render(mainContainer);
        break;
      case 'chains':
        this.renderChainsListView(mainContainer);
        break;
      case 'chain_detail':
        ChainViewComponent.render(mainContainer, params.chainId || Store.state.activeChainId);
        break;
      case 'parties':
        PartyLedgerComponent.render(mainContainer, params.partyId || Store.state.activePartyId);
        break;
      case 'communications':
        CommViewerComponent.render(mainContainer);
        break;
      case 'products':
        ProductMasterComponent.render(mainContainer);
        break;
      case 'reports':
        ReportsComponent.render(mainContainer);
        break;
      case 'busy':
        BusySettingsComponent.render(mainContainer);
        break;
      case 'trash':
        DeletedItemsComponent.render(mainContainer);
        break;
      case 'audit':
        AuditViewerComponent.render(mainContainer);
        break;
      case 'tests':
        TestRunnerComponent.render(mainContainer);
        break;
      default:
        DashboardComponent.render(mainContainer);
    }
    this.updateTrashBadge();
  },

  async updateTrashBadge() {
    try {
      const res = await API.getTrash('all');
      const count = (res.deleted_items || []).length;
      const badge = document.getElementById('sidebar-trash-count');
      if (badge) {
        badge.textContent = count > 0 ? count : '';
        badge.style.display = count > 0 ? 'inline-block' : 'none';
      }
    } catch (e) {}
  },

  viewChain(chainId) {
    Store.state.activeChainId = chainId;
    this.navigate('chain_detail', { chainId });
  },

  viewParty(partyId) {
    Store.state.activePartyId = partyId;
    this.navigate('parties', { partyId });
  },

  async renderChainsListView(container) {
    container.innerHTML = `
      <div class="animate-fade-in">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
          <div>
            <h1>Deal Chains & Lot Registers</h1>
            <p class="text-secondary" style="font-size: 0.875rem;">Explore complete multi-deal lots, track intermediate margins and inspect direct billing mandates</p>
          </div>
          <button class="btn btn-primary" onclick="App.navigate('new_deal')">
            <span>➕</span> Start New Chain
          </button>
        </div>

        <div class="card">
          <div class="table-responsive">
            <table class="data-table" id="chains-list-table">
              <thead>
                <tr>
                  <th>Chain Code</th>
                  <th>Product</th>
                  <th>Lot Quantity</th>
                  <th>Original Bill Seller</th>
                  <th>Final Bill Buyer</th>
                  <th>Final Rate + GST</th>
                  <th>Total Profit</th>
                  <th>Total Brokerage</th>
                  <th>Total Earning</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr><td colspan="11" style="text-align: center;">Loading deal chains...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    try {
      const res = await API.getChains();
      if (!res.success) return;

      const tbody = document.querySelector('#chains-list-table tbody');
      if (res.chains.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" style="text-align: center;">No active chains found.</td></tr>';
        return;
      }

      tbody.innerHTML = res.chains.map(c => `
        <tr>
          <td><strong style="color: var(--text-gold); font-family: var(--font-mono);">${c.chain_code}</strong></td>
          <td><span class="badge badge-info">${c.product_code || c.product_name}</span></td>
          <td>${Store.formatQty(c.initial_quantity_qtl)}</td>
          <td>${c.original_bill_seller_name || 'N/A'}</td>
          <td><strong>${c.final_bill_buyer_name || 'Awaiting Resale'}</strong></td>
          <td class="font-mono">₹${Number(c.final_billing_rate).toLocaleString('en-IN')}/Qtl</td>
          <td class="font-mono text-profit font-bold">${Store.formatINR(c.total_price_diff_profit)}</td>
          <td class="font-mono text-gold font-bold">${Store.formatINR(c.total_brokerage)}</td>
          <td class="font-mono" style="color: #38bdf8; font-weight: 700;">${Store.formatINR(c.total_chain_earning)}</td>
          <td><span class="badge badge-${c.status}">${c.status}</span></td>
          <td>
            <div style="display: flex; gap: 6px; align-items: center;">
              <button class="btn btn-sm btn-primary" onclick="App.viewChain(${c.id})">
                <span>🔍</span> Inspect
              </button>
              <button 
                class="btn btn-sm btn-outline-danger" 
                title="Delete Chain"
                style="padding: 4px 8px; font-size: 11px; border-color: rgba(239, 68, 68, 0.4); color: var(--danger-red);"
                onclick="App.deleteChain(${c.id}, '${c.chain_code}')"
              >
                🗑️
              </button>
            </div>
          </td>
        </tr>
      `).join('');

    } catch (err) {
      Store.showToast('Error loading chains: ' + err.message, 'error');
    }
  },

  async deleteChain(chainId, chainCode) {
    if (!confirm(`Are you sure you want to delete Deal Chain ${chainCode} and all its linked deals?\n\nIt will be moved to Deleted Items where you can restore it anytime.`)) {
      return;
    }

    try {
      await API.deleteChain(chainId, 'Deleted from chains list table');
      Store.showToast(`Deal Chain ${chainCode} deleted.`, 'warning', async () => {
        await API.restoreChain(chainId);
        Store.showToast(`Deal Chain ${chainCode} restored successfully!`, 'success');
        App.renderChainsListView(document.getElementById('main-content'));
      });
      this.renderChainsListView(document.getElementById('main-content'));
    } catch (err) {
      Store.showToast(`Failed to delete chain: ${err.message}`, 'error');
    }
  },

  switchRole(role) {
    const roleProfiles = {
      admin: { user_id: 1, username: 'admin', role: 'admin', full_name: 'G&C Administrator' },
      broker: { user_id: 2, username: 'broker', role: 'broker', full_name: 'Senior Oil Broker' },
      accounts: { user_id: 3, username: 'accounts', role: 'accounts', full_name: 'Accounts Head' },
      viewer: { user_id: 4, username: 'viewer', role: 'viewer', full_name: 'Management Viewer' }
    };

    const targetUser = roleProfiles[role] || roleProfiles.admin;
    Store.setUser(targetUser);
    Store.showToast(`Switched active session to: ${targetUser.full_name} (${targetUser.role.toUpperCase()})`, 'info');
    
    // Re-render current tab to apply role restrictions
    this.navigate(Store.state.currentTab);
  },

  updateUserUI(user) {
    const nameEl = document.getElementById('top-user-name');
    const roleEl = document.getElementById('top-user-role');
    const selectEl = document.getElementById('role-switcher-select');

    if (nameEl) nameEl.innerText = user.full_name;
    if (roleEl) roleEl.innerText = user.role.toUpperCase();
    if (selectEl && selectEl.value !== user.role) selectEl.value = user.role;
  }
};

// Boot App on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
