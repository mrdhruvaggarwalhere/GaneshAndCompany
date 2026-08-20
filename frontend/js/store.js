/**
 * G&C Central Deal and Brokerage Automation Platform
 * Global Reactive Store, Formatting Utilities & Modal Manager
 */

const Store = {
  state: {
    isAuthenticated: Boolean(localStorage.getItem('gnc_auth_token')),
    currentUser: (() => {
      try {
        const saved = localStorage.getItem('gnc_user');
        return saved ? JSON.parse(saved) : null;
      } catch (e) {
        return null;
      }
    })(),
    parties: [],
    products: [],
    currentTab: 'dashboard',
    activeChainId: null,
    activePartyId: null,
  },

  listeners: [],

  subscribe(fn) {
    this.listeners.push(fn);
  },

  notify() {
    this.listeners.forEach(fn => fn(this.state));
  },

  setAuth(user, token) {
    if (token) localStorage.setItem('gnc_auth_token', token);
    if (user) localStorage.setItem('gnc_user', JSON.stringify(user));
    this.state.currentUser = user;
    this.state.isAuthenticated = true;
    this.notify();
  },

  clearAuth() {
    localStorage.removeItem('gnc_auth_token');
    localStorage.removeItem('gnc_user');
    this.state.currentUser = null;
    this.state.isAuthenticated = false;
    this.notify();
  },

  setUser(user) {
    this.state.currentUser = user;
    if (user) localStorage.setItem('gnc_user', JSON.stringify(user));
    this.notify();
  },

  setParties(parties) {
    this.state.parties = parties;
    this.notify();
  },

  setProducts(products) {
    this.state.products = products;
    this.notify();
  },

  setTab(tab) {
    this.state.currentTab = tab;
    this.notify();
  },

  can(permissionKey) {
    const role = this.state.currentUser?.role || 'admin';
    const roleMap = {
      admin: true,
      broker: ['deals.create', 'deals.edit', 'deals.resell', 'deals.override_brokerage', 'parties.manage', 'reports.view', 'excel.export'].includes(permissionKey),
      accounts: ['parties.manage', 'reports.view', 'excel.export', 'billing.approve', 'payments.manage', 'busy.manage', 'audit.view'].includes(permissionKey),
      viewer: ['reports.view'].includes(permissionKey)
    };
    if (role === 'admin') return true;
    return Boolean(roleMap[role]);
  },

  // Formatting Utilities
  formatINR(amount) {
    if (amount === undefined || amount === null || isNaN(Number(amount))) {
      return '₹0.00';
    }
    const num = Number(amount);
    const isNegative = num < 0;
    const absVal = Math.abs(num);
    const parts = absVal.toFixed(2).split('.');
    let intPart = parts[0];
    const decPart = parts[1];

    if (intPart.length > 3) {
      const lastThree = intPart.substring(intPart.length - 3);
      const remaining = intPart.substring(0, intPart.length - 3);
      intPart = remaining.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + lastThree;
    }

    return `${isNegative ? '-' : ''}₹${intPart}.${decPart}`;
  },

  formatDate(isoDate) {
    if (!isoDate) return '';
    try {
      const s = String(isoDate).slice(0, 10);
      const parts = s.split('-');
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`; // DD/MM/YYYY
      }
    } catch (e) {}
    return isoDate;
  },

  formatQty(qtl) {
    const q = Number(qtl || 0);
    const t = q / 10;
    return `${t.toLocaleString('en-IN', { maximumFractionDigits: 3 })} MT (${q.toLocaleString('en-IN', { maximumFractionDigits: 2 })} Qtl)`;
  },

  showToast(message, type = 'info', undoCallback = null) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '⚠️';
    if (type === 'warning') icon = '🗑️';

    let html = `<span>${icon}</span><div style="flex:1;">${message}</div>`;
    if (undoCallback && typeof undoCallback === 'function') {
      html += `<button class="btn btn-secondary btn-sm toast-undo-btn" style="margin-left:12px; padding:3px 10px; font-size:12px; font-weight:700; background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.3); color:#fff; border-radius:6px; cursor:pointer;">↩️ Undo</button>`;
    }

    toast.innerHTML = html;
    container.appendChild(toast);

    if (undoCallback) {
      const btn = toast.querySelector('.toast-undo-btn');
      if (btn) {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          btn.disabled = true;
          btn.textContent = 'Restoring...';
          try {
            await undoCallback();
            toast.remove();
          } catch (err) {
            Store.showToast(`Undo failed: ${err.message}`, 'error');
          }
        });
      }
    }

    const duration = undoCallback ? 8000 : 4000;
    setTimeout(() => {
      if (toast.parentNode) {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
      }
    }, duration);
  },

  openModal(title, bodyHtml, footerHtml = '') {
    const overlay = document.getElementById('global-modal');
    if (!overlay) return;

    document.getElementById('modal-title').innerHTML = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    document.getElementById('modal-footer').innerHTML = footerHtml;

    overlay.classList.add('active');
  },

  closeModal() {
    const overlay = document.getElementById('global-modal');
    if (overlay) overlay.classList.remove('active');
  }
};
