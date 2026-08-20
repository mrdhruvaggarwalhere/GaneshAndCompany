/**
 * Deal-Chain Detail & Visual Resale Flow Component
 */
const ChainViewComponent = {
  currentChainId: null,

  async render(container, chainId) {
    this.currentChainId = chainId || Store.state.activeChainId || 1;
    container.innerHTML = `
      <div class="animate-fade-in">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
          <div>
            <h1 id="chain-title">Deal Chain Flow: Loading...</h1>
            <p class="text-secondary" style="font-size: 0.875rem;">Internal Multi-Link Resale Trail & Final Commercial Billing Resolution</p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="btn btn-secondary" onclick="App.navigate('chains')">
              <span>←</span> All Chains
            </button>
            <button class="btn btn-outline-danger" onclick="ChainViewComponent.deleteCurrentChain()" style="border-color: rgba(239, 68, 68, 0.4); color: var(--danger-red);">
              <span>🗑️</span> Delete Entire Lot
            </button>
            <button class="btn btn-primary" onclick="ChainViewComponent.openResaleModal()">
              <span>🔄</span> Resell / Add Next Deal
            </button>
          </div>
        </div>

        <!-- Prominent Official Direct Billing Highlight Card -->
        <div class="direct-billing-banner" id="chain-billing-banner">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-gold); text-transform: uppercase;">
            Commercial Invoice Mandate
          </div>
          <div class="billing-instruction-text" id="billing-instruction-text">
            Loading official direct billing instruction...
          </div>
          
          <div class="billing-meta-grid">
            <div class="billing-meta-item">
              <span class="billing-meta-label">Original Bill Seller</span>
              <span class="billing-meta-value highlight-seller" id="meta-orig-seller">-</span>
            </div>
            <div class="billing-meta-item">
              <span class="billing-meta-label">Final Bill Buyer</span>
              <span class="billing-meta-value highlight-buyer" id="meta-final-buyer">-</span>
            </div>
            <div class="billing-meta-item">
              <span class="billing-meta-label">Final Billing Rate</span>
              <span class="billing-meta-value highlight-rate" id="meta-final-rate">₹0.00 / Qtl</span>
            </div>
            <div class="billing-meta-item">
              <span class="billing-meta-label">Total Chain Profit</span>
              <span class="billing-meta-value text-profit font-mono" id="meta-chain-profit">₹0.00</span>
            </div>
            <div class="billing-meta-item">
              <span class="billing-meta-label">Total Chain Brokerage</span>
              <span class="billing-meta-value text-gold font-mono" id="meta-chain-brokerage">₹0.00</span>
            </div>
            <div class="billing-meta-item">
              <span class="billing-meta-label">Total Broker Earning</span>
              <span class="billing-meta-value font-mono" style="color: #38bdf8;" id="meta-chain-earnings">₹0.00</span>
            </div>
          </div>

          <!-- Party-wise Chain Profit Realization Section -->
          <div id="party-profit-breakdown-container" style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border-subtle);">
            <!-- Rendered dynamically -->
          </div>

          <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border-subtle);">
            <button class="btn btn-sm btn-success" style="background: #22c55e; color: #000; font-weight: 700;" onclick="CommModalComponent.open({ message_type: 'final_billing_instruction', chain_id: ChainViewComponent.currentChainId })">
              <span>💬</span> Send Billing Instruction (WhatsApp / Email)
            </button>
            <button class="btn btn-sm btn-success" id="btn-approve-billing" onclick="ChainViewComponent.approveBilling()" style="display: none;">
              <span>✅</span> Approve Final Commercial Billing
            </button>
            <button class="btn btn-sm btn-outline-gold" onclick="ChainViewComponent.copyInstruction()">
              <span>📋</span> Copy Mandate
            </button>
            <button class="btn btn-sm btn-secondary" onclick="ChainViewComponent.stageBusyVoucher()">
              <span>⚡</span> Prepare BUSY Voucher
            </button>
          </div>
        </div>

        <!-- Chronological Timeline & Resale Links Table -->
        <div class="card" style="margin-bottom: 24px;">
          <div class="card-header">
            <div class="card-title"><span>⛓️</span> Internal Deal-Chain Sequence (Audit & Margin Trail)</div>
            <button class="btn btn-sm btn-primary" onclick="ChainViewComponent.openResaleModal()">
              <span>➕</span> Add Next Resale Link
            </button>
          </div>

          <div class="deal-timeline" id="chain-timeline-list">
            <!-- Timeline nodes rendered dynamically -->
          </div>
        </div>
      </div>
    `;

    await this.loadData();
  },

  currentChainCode: '',

  async loadData() {
    try {
      const res = await API.getChain(this.currentChainId);
      if (!res.success) return;

      const ch = res.chain;
      const deals = res.deals || [];
      const totals = res.chain_totals;
      this.currentChainCode = ch.chain_code;

      document.getElementById('chain-title').innerText = `Deal Chain: ${ch.chain_code} (${ch.product_name})`;
      document.getElementById('billing-instruction-text').innerHTML = totals.direct_billing_instruction;
      
      document.getElementById('meta-orig-seller').innerText = totals.original_bill_seller_name || 'N/A';
      document.getElementById('meta-final-buyer').innerText = totals.final_bill_buyer_name || 'N/A';
      document.getElementById('meta-final-rate').innerText = `₹${Number(totals.final_billing_rate).toLocaleString('en-IN')}/Qtl`;
      document.getElementById('meta-chain-profit').innerText = Store.formatINR(totals.total_price_diff_profit);
      document.getElementById('meta-chain-brokerage').innerText = Store.formatINR(totals.total_brokerage);
      document.getElementById('meta-chain-earnings').innerText = Store.formatINR(totals.total_chain_earning);

      // Show/hide Approve Billing button based on chain status and RBAC
      const approveBtn = document.getElementById('btn-approve-billing');
      const resellBtn = document.querySelector('button[onclick="ChainViewComponent.openResaleModal()"]');
      const isBilledOrCancelled = ch.status === 'billed' || ch.status === 'cancelled';
      if (approveBtn) {
        const canApproveBilling = Store.can('billing.approve');
        const chainNotYetBilled = ch.status !== 'billed' && ch.status !== 'cancelled';
        approveBtn.style.display = (canApproveBilling && chainNotYetBilled) ? 'inline-flex' : 'none';
      }
      // Disable Resell button for finalized chains
      document.querySelectorAll('button[onclick="ChainViewComponent.openResaleModal()"]').forEach(btn => {
        if (isBilledOrCancelled) {
          btn.disabled = true;
          btn.title = `Chain is ${ch.status} — no further resale links can be added.`;
          btn.style.opacity = '0.4';
          btn.style.cursor = 'not-allowed';
        } else {
          btn.disabled = false;
          btn.style.opacity = '';
          btn.style.cursor = '';
        }
      });

      // Render Party Profit Breakdown Card
      const profitBreakdownContainer = document.getElementById('party-profit-breakdown-container');
      const breakdown = totals.party_profit_breakdown || [];
      if (breakdown.length > 0) {
        const isTotalLoss = totals.total_price_diff_profit < 0;
        const totalBadgeClass = isTotalLoss ? 'badge-loss' : 'badge-profit';
        const totalSign = isTotalLoss ? '' : '+';

        profitBreakdownContainer.innerHTML = `
          <div style="background: rgba(34, 197, 94, 0.07); border: 1px solid rgba(34, 197, 94, 0.25); border-radius: var(--radius-md); padding: 12px 16px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
              <span style="font-size: 0.8125rem; font-weight: 700; color: #4ade80; text-transform: uppercase; letter-spacing: 0.5px;">
                💰 Party-wise Chain Profit Receivables (Who Pays Margin Profit)
              </span>
              <span class="badge ${totalBadgeClass} font-mono" style="font-weight: 700;">
                Total Realized: ${totalSign}${Store.formatINR(totals.total_price_diff_profit)}
              </span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px;">
              ${breakdown.map(item => {
                const isLoss = item.profit_amount < 0;
                const sign = isLoss ? '' : '+';
                const colorClass = isLoss ? 'text-loss' : 'text-profit';
                const borderColor = isLoss ? '#ef4444' : '#22c55e';
                const labelColor = isLoss ? '#fca5a5' : '#4ade80';
                const diffSign = item.diff_per_qtl >= 0 ? '+' : '-';
                
                return `
                <div style="background: rgba(0,0,0,0.3); padding: 10px 12px; border-radius: 6px; border-left: 3px solid ${borderColor};">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: ${labelColor}; font-size: 0.875rem;">${item.payer_party_name}</strong>
                    <span class="font-mono ${colorClass} font-bold" style="font-size: 0.95rem;">${sign}${Store.formatINR(item.profit_amount)}</span>
                  </div>
                  <div class="text-muted" style="font-size: 0.75rem; margin-top: 4px;">
                    Link #${item.link_index} (${item.deal_number}): Auth @ ₹${Number(item.authorized_rate).toLocaleString('en-IN')} ➔ Actual @ ₹${Number(item.actual_rate).toLocaleString('en-IN')} (${diffSign}₹${Math.abs(item.diff_per_qtl)}/Qtl on ${item.quantity_qtl} Qtl)
                  </div>
                </div>
              `}).join('')}
            </div>
          </div>
        `;
      } else {
        profitBreakdownContainer.innerHTML = '';
      }

      // Render Timeline Nodes
      const timelineContainer = document.getElementById('chain-timeline-list');
      if (deals.length === 0) {
        timelineContainer.innerHTML = '<div class="text-muted">No deals found in this chain.</div>';
        return;
      }

      timelineContainer.innerHTML = deals.map((d, index) => {
        const isResale = index > 0;
        const diff = Number(d.price_diff_per_qtl || 0);
        const profit = Number(d.price_diff_profit || 0);

        return `
          <div class="timeline-node ${d.status === 'cancelled' ? 'cancelled' : ''}">
            <div class="timeline-dot ${d.status === 'completed' ? 'completed' : ''}"></div>
            
            <div class="timeline-header">
              <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-weight: 700; color: var(--text-gold); font-size: 0.95rem;">
                  Link #${index + 1}: ${d.deal_number}
                </span>
                <span class="text-muted" style="font-size: 0.75rem;">
                  Deal Date: ${Store.formatDate(d.deal_date)} | Delivery: ${Store.formatDate(d.delivery_date)}
                </span>
              </div>
              <div style="display: flex; gap: 8px; align-items: center;">
                <span class="badge badge-${d.status}">${d.status}</span>
                ${d.status !== 'cancelled' && Store.can('deals.cancel') ? `
                  <button class="btn btn-sm btn-outline-danger" style="padding: 2px 8px; font-size: 0.7rem;" onclick="ChainViewComponent.cancelDeal(${d.id})">
                    Cancel
                  </button>
                ` : ''}
                <button 
                  class="btn btn-sm btn-outline-danger" 
                  title="Delete Deal"
                  style="padding: 2px 8px; font-size: 0.75rem; border-color: rgba(239, 68, 68, 0.4); color: var(--danger-red);"
                  onclick="ChainViewComponent.deleteDeal(${d.id}, '${d.deal_number}')"
                >
                  <span>🗑️</span> Delete
                </button>
              </div>
            </div>

            <div class="timeline-parties">
              <span style="color: #38bdf8; font-weight: 600;">${d.seller_name} <small style="color: var(--text-muted); font-size: 0.75rem;">(Seller)</small></span>
              <span class="timeline-arrow">➔</span>
              <span style="color: #4ade80; font-weight: 600;">
                ${d.buyer_name} <small style="color: var(--text-muted); font-size: 0.75rem;">(Buyer / Giver)</small>
                ${d.authorized_rate_per_qtl > 0 ? `<span class="badge badge-info" style="font-size: 0.7rem; margin-left: 6px;">Buyer Auth @ ₹${Number(d.authorized_rate_per_qtl).toLocaleString('en-IN')}/-</span>` : ''}
              </span>
            </div>

            <div class="timeline-metrics">
              <div>
                <span class="text-muted">Quantity:</span>
                <div class="font-mono" style="font-weight: 600;">${Store.formatQty(d.quantity_qtl)}</div>
              </div>
              <div>
                <span class="text-muted">Actual Sale Rate:</span>
                <div class="font-mono" style="font-weight: 600; color: var(--text-gold);">
                  ₹${Number(d.actual_rate_per_qtl || d.rate_per_qtl).toLocaleString('en-IN')}/Qtl ${d.gst_applicable ? '+ GST' : ''}
                </div>
              </div>
              ${isResale ? `
                <div>
                  <span class="text-muted">Price Difference:</span>
                  <div class="font-mono ${diff >= 0 ? 'text-profit' : 'text-loss'}" style="font-weight: 700;">
                    ${diff >= 0 ? '+' : ''}₹${diff}/Qtl (Profit: ${Store.formatINR(profit)})
                  </div>
                </div>
              ` : `
                <div>
                  <span class="text-muted">Type:</span>
                  <div style="font-weight: 600; color: var(--info-blue);">Root Lot Purchase (Buyer gives order)</div>
                </div>
              `}
              <div>
                <span class="text-muted">Brokerage:</span>
                <div class="font-mono" style="font-weight: 600; color: var(--text-gold);">
                  Buyer: ${Store.formatINR(d.buyer_brokerage_amount)} | Seller: ${Store.formatINR(d.seller_brokerage_amount)}
                </div>
              </div>
            </div>

            ${(profit !== 0 && d.authorized_rate_per_qtl > 0) ? `
              <div style="background: rgba(${profit > 0 ? '34, 197, 94' : '239, 68, 68'}, 0.08); border: 1px solid rgba(${profit > 0 ? '34, 197, 94' : '239, 68, 68'}, 0.25); padding: 8px 12px; border-radius: 6px; margin-top: 8px; font-size: 0.8125rem; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <strong style="color: ${profit > 0 ? '#4ade80' : '#fca5a5'};">💰 Chain ${profit > 0 ? 'Profit' : 'Loss'} Receivable:</strong> 
                  <span class="font-mono ${profit > 0 ? 'text-profit' : 'text-loss'}" style="font-weight: 700; margin-left: 4px;">${profit > 0 ? '+' : ''}${Store.formatINR(profit)}</span>
                  <span class="text-muted" style="margin-left: 6px;">from buyer <strong>${d.buyer_name}</strong></span>
                </div>
                <div class="text-muted font-mono" style="font-size: 0.75rem;">
                  Auth: ₹${Number(d.authorized_rate_per_qtl).toLocaleString('en-IN')} ➔ Sale: ₹${Number(d.actual_rate_per_qtl).toLocaleString('en-IN')}
                </div>
              </div>
            ` : ''}

            <!-- One-Click Communication Toolbar -->
            <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center; justify-content: space-between; margin-top: 10px; padding-top: 8px; border-top: 1px dashed var(--border-subtle);">
              <span class="text-muted" style="font-size: 0.7rem; font-weight: 600;">💬 One-Click Client Dispatch:</span>
              <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                <button class="btn btn-sm btn-secondary" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.open({ message_type: 'deal_confirmation_buyer', deal_id: ${d.id}, party_id: ${d.buyer_id} })" title="Send Deal Confirmation to Buyer">
                  <span>📱</span> Buyer Confirmation
                </button>
                <button class="btn btn-sm btn-secondary" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.open({ message_type: 'deal_confirmation_seller', deal_id: ${d.id}, party_id: ${d.seller_id} })" title="Send Deal Confirmation to Seller">
                  <span>✉️</span> Seller Confirmation
                </button>
                <button class="btn btn-sm btn-secondary" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.open({ message_type: 'rate_confirmation', deal_id: ${d.id}, party_id: ${d.buyer_id} })" title="Send Rate Confirmation">
                  <span>📊</span> Rate Confirmation
                </button>
                <button class="btn btn-sm btn-secondary" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.open({ message_type: 'delivery_reminder', deal_id: ${d.id} })" title="Send Delivery Reminder">
                  <span>🚚</span> Delivery Reminder
                </button>
                <button class="btn btn-sm btn-secondary" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.open({ message_type: 'deal_amendment', deal_id: ${d.id} })" title="Send Deal Amendment">
                  <span>✏️</span> Amendment
                </button>
                ${d.status === 'cancelled' ? `
                  <button class="btn btn-sm btn-outline-danger" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.open({ message_type: 'deal_cancellation', deal_id: ${d.id} })" title="Send Deal Cancellation">
                    <span>❌</span> Cancellation Notice
                  </button>
                ` : ''}
                <button class="btn btn-sm btn-secondary" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.open({ message_type: 'custom_message', deal_id: ${d.id}, party_id: ${d.buyer_id} })" title="Send Custom Message">
                  <span>📝</span> Custom Note
                </button>
              </div>
            </div>

            ${d.notes ? `<div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 8px; italic">Note: ${d.notes}</div>` : ''}
            ${d.cancellation_reason ? `<div style="font-size: 0.75rem; color: var(--loss-red); margin-top: 8px;">Cancellation Reason: ${d.cancellation_reason}</div>` : ''}
          </div>
        `;
      }).join('');

    } catch (err) {
      Store.showToast('Error loading chain detail: ' + err.message, 'error');
    }
  },

  async openResaleModal() {
    const res = await API.getChain(this.currentChainId);
    if (!res.success) return;

    const ch = res.chain;
    const deals = res.deals || [];
    const latestDeal = deals[deals.length - 1];

    if (!latestDeal) {
      Store.showToast('No active deal found to resell.', 'error');
      return;
    }

    const parties = Store.state.parties || [];
    const instructingSeller = latestDeal.buyer_name;
    const instructingSellerId = latestDeal.buyer_id;

    const buyerOptions = parties
      .filter(p => p.id !== instructingSellerId)
      .map(p => `<option value="${p.id}" data-buyer-brok="${p.default_buyer_brokerage_rate}">${p.name} (${p.city || 'India'})</option>`)
      .join('');

    const today = new Date().toISOString().slice(0, 10);
    const defaultAuthRate = latestDeal.rate_per_qtl;

    const bodyHtml = `
      <form id="resale-modal-form" onsubmit="ChainViewComponent.handleResaleSubmit(event)">
        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); padding: 12px; border-radius: var(--radius-md); margin-bottom: 16px;">
          <div style="font-size: 0.8125rem; font-weight: 700; color: var(--text-gold);">
            🔄 Reselling Lot Quantity from Previous Buyer
          </div>
          <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px;">
            Instructing Seller: <strong>${instructingSeller}</strong> | Available Balance: <strong>${ch.remaining_quantity_qtl} Qtl (${ch.remaining_quantity_qtl / 10} MT)</strong>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Instruction Date *</label>
            <input type="date" id="resale_instruction_date" class="form-control" value="${today}" required>
          </div>
          <div class="form-group">
            <label class="form-label">Deal / Resale Date *</label>
            <input type="date" id="resale_deal_date" class="form-control" value="${today}" required>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Actual Next Buyer Party *</label>
          <select id="resale_buyer_id" class="form-select" required onchange="ChainViewComponent.recalcResale()">
            <option value="">-- Select Next Buyer --</option>
            ${buyerOptions}
          </select>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">
              <span>Party Authorized Rate (₹/Qtl) *</span>
              <span class="unit-badge">Base Rate</span>
            </label>
            <input type="number" step="0.01" id="resale_auth_rate" class="form-control font-mono" value="${defaultAuthRate}" required oninput="ChainViewComponent.recalcResale()">
          </div>
          <div class="form-group">
            <label class="form-label">
              <span>Actual Resale Rate (₹/Qtl) *</span>
              <span class="unit-badge">Per Qtl</span>
            </label>
            <input type="number" step="0.01" id="resale_actual_rate" class="form-control font-mono" placeholder="e.g. 16475" required oninput="ChainViewComponent.recalcResale()">
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Resale Quantity (Quintals) *</label>
            <input type="number" step="0.01" id="resale_qty_qtl" class="form-control font-mono" value="${ch.remaining_quantity_qtl}" max="${ch.remaining_quantity_qtl}" required oninput="ChainViewComponent.recalcResale()">
          </div>
          <div class="form-group">
            <label class="form-label">Target Delivery Date *</label>
            <input type="date" id="resale_delivery_date" class="form-control" value="${latestDeal.delivery_date || today}" required>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Buyer Brokerage (₹/Tonne)</label>
            <input type="number" step="0.01" id="resale_buyer_brok" class="form-control font-mono" value="50.0" oninput="ChainViewComponent.recalcResale()">
          </div>
          <div class="form-group">
            <label class="form-label">Seller Brokerage (₹/Tonne)</label>
            <input type="number" step="0.01" id="resale_seller_brok" class="form-control font-mono" value="50.0" oninput="ChainViewComponent.recalcResale()">
          </div>
        </div>

        <!-- Live Resale Margin Preview Box -->
        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-medium); border-radius: var(--radius-md); padding: 14px; margin-top: 8px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.8125rem; margin-bottom: 6px;">
            <span class="text-secondary">Rate Difference per Quintal:</span>
            <span class="font-mono font-bold" id="resale-prev-diff">₹0.00 / Qtl</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.95rem; font-weight: 700; margin-bottom: 6px;">
            <span>Price-Difference Margin Profit:</span>
            <span class="font-mono text-profit" id="resale-prev-profit">₹0.00</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.8125rem;">
            <span class="text-secondary">Total Link Brokerage:</span>
            <span class="font-mono text-gold" id="resale-prev-brok">₹0.00</span>
          </div>
        </div>
      </form>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="Store.closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="document.getElementById('resale-modal-form').requestSubmit()">
        <span>💾</span> Save Resale Deal
      </button>
    `;

    Store.openModal(`Add Next Resale Link (Chain ${ch.chain_code})`, bodyHtml, footerHtml);
    this.recalcResale();
  },

  recalcResale() {
    const authRate = Number(document.getElementById('resale_auth_rate')?.value || 0);
    const actualRate = Number(document.getElementById('resale_actual_rate')?.value || 0);
    const qtyQtl = Number(document.getElementById('resale_qty_qtl')?.value || 0);
    const tonnes = qtyQtl / 10;

    const bBrok = Number(document.getElementById('resale_buyer_brok')?.value || 0);
    const sBrok = Number(document.getElementById('resale_seller_brok')?.value || 0);

    const diff = actualRate - authRate;
    const profit = diff * qtyQtl;
    const totalBrok = tonnes * (bBrok + sBrok);

    const diffEl = document.getElementById('resale-prev-diff');
    const profitEl = document.getElementById('resale-prev-profit');
    const brokEl = document.getElementById('resale-prev-brok');

    if (diffEl) {
      diffEl.innerText = `${diff >= 0 ? '+' : ''}₹${diff.toFixed(2)} / Qtl`;
      diffEl.className = `font-mono ${diff >= 0 ? 'text-profit' : 'text-loss'}`;
    }
    if (profitEl) {
      profitEl.innerText = Store.formatINR(profit);
      profitEl.className = `font-mono ${profit >= 0 ? 'text-profit' : 'text-loss'}`;
    }
    if (brokEl) {
      brokEl.innerText = Store.formatINR(totalBrok);
    }
  },

  async handleResaleSubmit(event) {
    event.preventDefault();
    const buyerId = document.getElementById('resale_buyer_id').value;
    if (!buyerId) {
      Store.showToast('Please select next buyer party.', 'error');
      return;
    }

    const payload = {
      instruction_date: document.getElementById('resale_instruction_date').value,
      deal_date: document.getElementById('resale_deal_date').value,
      delivery_date: document.getElementById('resale_delivery_date').value,
      buyer_id: Number(buyerId),
      authorized_rate_per_qtl: Number(document.getElementById('resale_auth_rate').value),
      actual_rate_per_qtl: Number(document.getElementById('resale_actual_rate').value),
      rate_per_qtl: Number(document.getElementById('resale_actual_rate').value),
      quantity_qtl: Number(document.getElementById('resale_qty_qtl').value),
      buyer_brokerage_rate_per_tonne: Number(document.getElementById('resale_buyer_brok').value),
      seller_brokerage_rate_per_tonne: Number(document.getElementById('resale_seller_brok').value)
    };

    try {
      const res = await API.addResale(this.currentChainId, payload);
      if (res.success) {
        Store.closeModal();
        Store.showToast(`Resale deal ${res.deal_number} added with profit of ${Store.formatINR(res.summary.price_diff_profit)}!`, 'success');
        this.loadData();
      }
    } catch (err) {
      Store.showToast(`Error adding resale: ${err.message}`, 'error');
    }
  },

  async approveBilling() {
    if (!confirm('Are you sure you want to approve this official direct billing instruction?')) return;
    try {
      const res = await API.approveBilling(this.currentChainId);
      if (res.success) {
        Store.showToast('Official Direct Billing Mandate approved!', 'success');
        this.loadData();
      }
    } catch (err) {
      Store.showToast('Error approving billing: ' + err.message, 'error');
    }
  },

  copyInstruction() {
    const text = document.getElementById('billing-instruction-text').innerText;
    navigator.clipboard.writeText(text);
    Store.showToast('Official Direct Billing Mandate copied to clipboard!', 'success');
  },

  async stageBusyVoucher() {
    try {
      const res = await API.stageBusyVoucher({
        chain_id: this.currentChainId,
        voucher_type: 'sales_direct_invoice'
      });
      if (res.success) {
        Store.showToast('BUSY Direct Sales Invoice voucher prepared & staged successfully!', 'success');
        App.navigate('busy');
      }
    } catch (err) {
      Store.showToast('Error staging BUSY voucher: ' + err.message, 'error');
    }
  },

  cancelDeal(dealId) {
    const reason = prompt('Enter mandatory cancellation reason for this deal:');
    if (!reason || !reason.trim()) {
      Store.showToast('Cancellation aborted: Reason is mandatory.', 'error');
      return;
    }
    API.cancelDeal(dealId, reason.trim()).then(res => {
      if (res.success) {
        Store.showToast('Deal cancelled successfully.', 'success');
        this.loadData();
      }
    }).catch(err => {
      Store.showToast('Failed to cancel deal: ' + err.message, 'error');
    });
  },

  async deleteDeal(dealId, dealNumber) {
    if (!confirm(`Are you sure you want to delete Deal ${dealNumber}?\n\nIt will be moved to the Deleted Items recycle bin, and you can undo/restore it anytime.`)) {
      return;
    }

    try {
      await API.deleteDeal(dealId, 'Deleted from chain timeline');
      Store.showToast(`Deal ${dealNumber} deleted.`, 'warning', async () => {
        await API.restoreDeal(dealId);
        Store.showToast(`Deal ${dealNumber} restored successfully!`, 'success');
        ChainViewComponent.loadData();
      });
      this.loadData();
    } catch (err) {
      Store.showToast(`Failed to delete deal: ${err.message}`, 'error');
    }
  },

  async deleteCurrentChain() {
    const chainCode = this.currentChainCode || `CHN-${this.currentChainId}`;
    if (!confirm(`Are you sure you want to delete Deal Chain ${chainCode} and all its deals?\n\nIt will be moved to the Deleted Items recycle bin, and you can undo/restore it anytime.`)) {
      return;
    }

    try {
      const chainId = this.currentChainId;
      await API.deleteChain(chainId, 'Deleted from chain flow');
      Store.showToast(`Deal Chain ${chainCode} deleted.`, 'warning', async () => {
        await API.restoreChain(chainId);
        Store.showToast(`Deal Chain ${chainCode} restored successfully!`, 'success');
        App.navigate('chains');
      });
      App.navigate('chains');
    } catch (err) {
      Store.showToast(`Failed to delete chain: ${err.message}`, 'error');
    }
  }
};
