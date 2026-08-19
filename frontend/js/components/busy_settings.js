/**
 * Future BUSY Accounting Integration & Voucher Hub Component
 */
const BusySettingsComponent = {
  async render(container) {
    container.innerHTML = `
      <div class="animate-fade-in">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
          <div>
            <h1>BUSY Accounting Software Integration Hub</h1>
            <p class="text-secondary" style="font-size: 0.875rem;">Intermediate Voucher Generator, Ledger Mapping & Accounting Staging Layer</p>
          </div>
          <button class="btn btn-primary" onclick="BusySettingsComponent.openVoucherGeneratorModal()">
            <span>⚡</span> Generate Test Intermediate Voucher
          </button>
        </div>

        <!-- Safeguard Alert Notice -->
        <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); padding: 16px; border-radius: var(--radius-lg); margin-bottom: 24px; display: flex; align-items: flex-start; gap: 14px;">
          <div style="font-size: 1.5rem;">🛡️</div>
          <div>
            <div style="font-weight: 700; color: #38bdf8; font-size: 0.95rem;">
              Accounting Isolation & Safeguard Protection Active
            </div>
            <div class="text-secondary" style="font-size: 0.8125rem; margin-top: 4px; line-height: 1.4;">
              Internal intermediate deal-chain records (speculative commitments, internal buyer-seller margins) are strictly segregated and blocked from posting as commercial invoices. Only <strong>Approved Direct Billing Instructions (Original Bill Seller ➔ Final Bill Buyer)</strong> and <strong>Brokerage Commission Journal Entries</strong> can be exported to BUSY.
            </div>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px;">
          
          <!-- Party Ledger Mappings -->
          <div class="card">
            <div class="card-header">
              <div class="card-title"><span>👥</span> BUSY Party Ledger Mappings</div>
            </div>
            <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
              <table class="data-table" id="busy-parties-table">
                <thead>
                  <tr>
                    <th>G&C Party Name</th>
                    <th>BUSY Ledger ID</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td colspan="3" style="text-align: center;">Loading mappings...</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Product Item Mappings -->
          <div class="card">
            <div class="card-header">
              <div class="card-title"><span>📦</span> BUSY Product / Item Mappings</div>
            </div>
            <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
              <table class="data-table" id="busy-products-table">
                <thead>
                  <tr>
                    <th>Product Code</th>
                    <th>Product Name</th>
                    <th>BUSY Item ID</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td colspan="3" style="text-align: center;">Loading mappings...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Sync Staging Queue -->
        <div class="card">
          <div class="card-header">
            <div class="card-title"><span>📤</span> BUSY Intermediate Voucher Queue & Sync Staging</div>
            <button class="btn btn-sm btn-secondary" onclick="BusySettingsComponent.loadQueue()"><span>🔄</span> Refresh Queue</button>
          </div>

          <div class="table-responsive">
            <table class="data-table" id="busy-queue-table">
              <thead>
                <tr>
                  <th>Voucher ID</th>
                  <th>Type</th>
                  <th>Chain Ref</th>
                  <th>Staged Date</th>
                  <th>Status</th>
                  <th>External BUSY Ref</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr><td colspan="7" style="text-align: center;">Loading sync queue...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    await this.loadMappings();
    await this.loadQueue();
  },

  async loadMappings() {
    try {
      const res = await API.getBusyMappings();
      if (!res.success) return;

      const pTbody = document.querySelector('#busy-parties-table tbody');
      pTbody.innerHTML = res.party_mappings.map(p => `
        <tr>
          <td><strong>${p.name}</strong></td>
          <td><code>${p.busy_ledger_id || 'UNMAPPED'}</code></td>
          <td><span class="badge badge-${p.busy_ledger_id ? 'completed' : 'ready'}">${p.busy_ledger_id ? 'Mapped' : 'Pending'}</span></td>
        </tr>
      `).join('');

      const prTbody = document.querySelector('#busy-products-table tbody');
      prTbody.innerHTML = res.product_mappings.map(pr => `
        <tr>
          <td><span class="badge badge-info">${pr.code}</span></td>
          <td><strong>${pr.name}</strong></td>
          <td><code>${pr.busy_item_id || 'UNMAPPED'}</code></td>
        </tr>
      `).join('');

    } catch (err) {
      Store.showToast('Error loading BUSY mappings: ' + err.message, 'error');
    }
  },

  async loadQueue() {
    try {
      const res = await API.getBusyQueue();
      if (!res.success) return;

      const tbody = document.querySelector('#busy-queue-table tbody');
      if (res.queue.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No vouchers currently in sync queue. Stage a voucher from a Deal Chain!</td></tr>';
        return;
      }

      tbody.innerHTML = res.queue.map(q => `
        <tr>
          <td class="font-mono">#${q.id}</td>
          <td><span class="badge badge-info">${q.voucher_type}</span></td>
          <td><strong>${q.chain_code || 'Direct Journal'}</strong></td>
          <td>${Store.formatDate(q.created_at)}</td>
          <td><span class="badge badge-${q.status}">${q.status}</span></td>
          <td class="font-mono">${q.external_reference || 'Pending Sync'}</td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-sm btn-secondary" onclick="BusySettingsComponent.viewVoucherPayload(${q.id})">
                👁️ Inspect
              </button>
              ${q.status !== 'posted' ? `
                <button class="btn btn-sm btn-success" onclick="BusySettingsComponent.syncVoucher(${q.id})">
                  🚀 Post/Sync
                </button>
              ` : ''}
            </div>
          </td>
        </tr>
      `).join('');

    } catch (err) {
      Store.showToast('Error loading sync queue: ' + err.message, 'error');
    }
  },

  async syncVoucher(queueId) {
    try {
      const res = await API.syncBusyVoucher(queueId);
      if (res.success) {
        Store.showToast(res.message, 'success');
        this.loadQueue();
      }
    } catch (err) {
      Store.showToast('Error synchronizing with BUSY: ' + err.message, 'error');
    }
  },

  async viewVoucherPayload(queueId) {
    const res = await API.getBusyQueue();
    if (!res.success) return;

    const item = res.queue.find(q => q.id === queueId);
    if (!item) return;

    let payloadObj = {};
    try {
      payloadObj = JSON.parse(item.voucher_payload_json);
    } catch (e) {}

    const bodyHtml = `
      <div>
        <div style="display: flex; gap: 10px; margin-bottom: 12px;">
          <button class="btn btn-sm btn-primary" onclick="document.getElementById('xml-view').style.display='block'; document.getElementById('json-view').style.display='none';">
            Standard XML Payload
          </button>
          <button class="btn btn-sm btn-secondary" onclick="document.getElementById('xml-view').style.display='none'; document.getElementById('json-view').style.display='block';">
            Intermediate JSON Payload
          </button>
        </div>

        <div id="xml-view" class="code-box">
${escapeHtml(payloadObj.xml_payload || 'XML generation applicable for Sales Invoices')}
        </div>

        <div id="json-view" class="code-box" style="display: none;">
${escapeHtml(JSON.stringify(payloadObj.json_payload || payloadObj, null, 2))}
        </div>
      </div>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="Store.closeModal()">Close</button>
      <button class="btn btn-primary" onclick="navigator.clipboard.writeText(document.getElementById('xml-view').innerText); Store.showToast('Payload copied to clipboard!', 'success');">
        📋 Copy XML
      </button>
    `;

    Store.openModal(`Inspect BUSY Voucher Payload (#${queueId})`, bodyHtml, footerHtml);
  },

  async openVoucherGeneratorModal() {
    const chainsRes = await API.getChains();
    const chains = chainsRes.chains || [];

    const bodyHtml = `
      <form id="voucher-gen-form" onsubmit="BusySettingsComponent.handleGenSubmit(event)">
        <div class="form-group">
          <label class="form-label">Select Approved Deal Chain for Direct Invoice *</label>
          <select id="gen_chain_id" class="form-select" required>
            ${chains.map(c => `<option value="${c.id}">${c.chain_code} (${c.product_name} - ${c.remaining_quantity_qtl} Qtl) [Status: ${c.status}]</option>`).join('')}
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">Voucher Type</label>
          <select id="gen_voucher_type" class="form-select">
            <option value="sales_direct_invoice">Official Direct Sales Invoice (Original Seller ➔ Final Buyer)</option>
          </select>
        </div>
      </form>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="Store.closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="document.getElementById('voucher-gen-form').requestSubmit()">
        ⚡ Generate & Stage Voucher
      </button>
    `;

    Store.openModal('Generate Intermediate BUSY Voucher', bodyHtml, footerHtml);
  },

  async handleGenSubmit(event) {
    event.preventDefault();
    const chainId = document.getElementById('gen_chain_id').value;
    const voucherType = document.getElementById('gen_voucher_type').value;

    try {
      const res = await API.stageBusyVoucher({
        chain_id: Number(chainId),
        voucher_type: voucherType
      });
      if (res.success) {
        Store.closeModal();
        Store.showToast('Voucher generated and staged in queue!', 'success');
        this.loadQueue();
      }
    } catch (err) {
      Store.showToast('Failed: ' + err.message, 'error');
    }
  }
};

function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
