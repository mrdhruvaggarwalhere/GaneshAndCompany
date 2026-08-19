/**
 * G&C Central Deal and Brokerage Automation Platform
 * API Client & Network Service
 */
const API = {
  baseUrl: window.location.origin,

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    const token = localStorage.getItem('gnc_auth_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      // Handle binary downloads (Excel files)
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('spreadsheetml') || contentType.includes('octet-stream')) {
        const blob = await response.blob();
        return { isBlob: true, blob, response };
      }

      const json = await response.json();
      if (!response.ok) {
        throw new Error(json.error || `HTTP ${response.status}: ${response.statusText}`);
      }
      return json;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  // Auth
  login: (username, password) => API.request('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  getMe: () => API.request('/api/auth/me'),

  // Dashboard
  getDashboard: () => API.request('/api/dashboard'),

  // Deals
  getDeals: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return API.request(`/api/deals?${q}`);
  },
  getDeal: (id) => API.request(`/api/deals/${id}`),
  createDeal: (data) => API.request('/api/deals', { method: 'POST', body: JSON.stringify(data) }),
  updateDeal: (id, data) => API.request(`/api/deals/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  cancelDeal: (id, reason) => API.request(`/api/deals/${id}/cancel`, { method: 'POST', body: JSON.stringify({ reason }) }),
  deleteDeal: (id, reason = 'User deleted deal') => API.request(`/api/deals/${id}/delete`, { method: 'POST', body: JSON.stringify({ reason }) }),
  restoreDeal: (id) => API.request(`/api/deals/${id}/restore`, { method: 'POST' }),

  // Chains
  getChains: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return API.request(`/api/chains?${q}`);
  },
  getChain: (id) => API.request(`/api/chains/${id}`),
  addResale: (chainId, data) => API.request(`/api/chains/${chainId}/resell`, { method: 'POST', body: JSON.stringify(data) }),
  approveBilling: (chainId) => API.request(`/api/chains/${chainId}/approve-billing`, { method: 'POST' }),
  deleteChain: (id, reason = 'User deleted lot/chain') => API.request(`/api/chains/${id}/delete`, { method: 'POST', body: JSON.stringify({ reason }) }),
  restoreChain: (id) => API.request(`/api/chains/${id}/restore`, { method: 'POST' }),

  // Parties
  getParties: () => API.request('/api/parties'),
  createParty: (data) => API.request('/api/parties', { method: 'POST', body: JSON.stringify(data) }),
  updateParty: (id, data) => API.request(`/api/parties/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteParty: (id, reason = 'User deleted party') => API.request(`/api/parties/${id}/delete`, { method: 'POST', body: JSON.stringify({ reason }) }),
  restoreParty: (id) => API.request(`/api/parties/${id}/restore`, { method: 'POST' }),
  getPartyLedger: (partyId) => API.request(`/api/parties/${partyId}/ledger`),
  recordPartyPayment: (partyId, data) => API.request(`/api/parties/${partyId}/payments`, { method: 'POST', body: JSON.stringify(data) }),
  deletePayment: (id, reason = 'User deleted payment') => API.request(`/api/payments/${id}/delete`, { method: 'POST', body: JSON.stringify({ reason }) }),
  restorePayment: (id) => API.request(`/api/payments/${id}/restore`, { method: 'POST' }),

  // Products
  getProducts: () => API.request('/api/products'),
  createProduct: (data) => API.request('/api/products', { method: 'POST', body: JSON.stringify(data) }),
  updateProduct: (id, data) => API.request(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProduct: (id, reason = 'User deleted product') => API.request(`/api/products/${id}/delete`, { method: 'POST', body: JSON.stringify({ reason }) }),
  restoreProduct: (id) => API.request(`/api/products/${id}/restore`, { method: 'POST' }),

  // Deleted Items / Recycle Bin / Trash
  getTrash: (type = 'all') => API.request(`/api/trash?type=${type}`),

  // Reports & Excel Export
  getReport: (type, params = {}) => {
    const q = new URLSearchParams({ type, ...params }).toString();
    return API.request(`/api/reports?${q}`);
  },
  downloadExcel: async (params = {}) => {
    const q = new URLSearchParams(params).toString();
    const result = await API.request(`/api/export/excel?${q}`);
    if (result.isBlob) {
      const url = window.URL.createObjectURL(result.blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `GNC_Brokerage_Register_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }
  },

  // BUSY Integration
  getBusyMappings: () => API.request('/api/busy/mappings'),
  getBusyQueue: () => API.request('/api/busy/queue'),
  stageBusyVoucher: (data) => API.request('/api/busy/generate-voucher', { method: 'POST', body: JSON.stringify(data) }),
  syncBusyVoucher: (queueId) => API.request('/api/busy/sync', { method: 'POST', body: JSON.stringify({ queue_id: queueId }) }),

  // Audit & Changelog
  getAuditTrail: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return API.request(`/api/audit?${q}`);
  },
  getAudit: (params = {}) => API.getAuditTrail(params),
  undoAuditEvent: (eventId) => API.request(`/api/audit/${eventId}/undo`, { method: 'POST' }),

  // Communication Module (Zero-Cost WhatsApp & Email)
  prepareCommunication: (data) => API.request('/api/communications/prepare', { method: 'POST', body: JSON.stringify(data) }),
  logCommunication: (data) => API.request('/api/communications/log', { method: 'POST', body: JSON.stringify(data) }),
  getCommunications: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return API.request(`/api/communications?${q}`);
  },
  updateCommunicationStatus: (id, data) => API.request(`/api/communications/${id}/status`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Test Runner
  runTests: () => API.request('/api/tests/run')
};

window.API = API;
