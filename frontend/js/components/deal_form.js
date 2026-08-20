/**
 * Fast Deal Entry & Resale Wizard Component
 */
const DealFormComponent = {
  render(container) {
    const today = new Date().toISOString().slice(0, 10);
    const parties = Store.state.parties || [];
    const products = Store.state.products || [];

    const partyOptions = parties.map(p => `
      <option value="${p.id}" data-buyer-brok="${p.default_buyer_brokerage_rate}" data-seller-brok="${p.default_seller_brokerage_rate}">
        ${p.name} (${p.city || 'India'})
      </option>
    `).join('');

    const productOptions = products.map(pr => `
      <option value="${pr.id}" data-gst="${pr.default_gst_pct}">
        ${pr.name} (${pr.code})
      </option>
    `).join('');

    container.innerHTML = `
      <div class="animate-fade-in" style="max-width: 1100px; margin: 0 auto;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
          <div>
            <h1>New Single-Entry Deal</h1>
            <p class="text-secondary" style="font-size: 0.875rem;">Create primary edible-oil purchase or start a new resale chain</p>
          </div>
          <button class="btn btn-secondary" onclick="App.navigate('dashboard')">
            <span>←</span> Back to Dashboard
          </button>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 24px;">
          
          <!-- Primary Deal Entry Form -->
          <div class="card">
            <form id="new-deal-form" onsubmit="DealFormComponent.handleSubmit(event)">
              
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="form-group">
                  <label class="form-label">Deal / Seller Date *</label>
                  <input type="date" id="deal_date" class="form-control" value="${today}" required onchange="DealFormComponent.recalc()">
                </div>
                <div class="form-group">
                  <label class="form-label">Delivery Target Date *</label>
                  <input type="date" id="delivery_date" class="form-control" value="${today}" required onchange="DealFormComponent.recalc()">
                </div>
              </div>

              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="form-group">
                  <label class="form-label">Seller Party (Supplier / Mill) *</label>
                  <select id="seller_id" class="form-select" required onchange="DealFormComponent.handleSellerChange()">
                    <option value="">-- Select Selling Party / Supplier --</option>
                    ${partyOptions}
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">Buyer Party (Order Giver / Purchaser) *</label>
                  <select id="buyer_id" class="form-select" required onchange="DealFormComponent.handleBuyerChange()">
                    <option value="">-- Select Buying Party (Order Giver) --</option>
                    ${partyOptions}
                  </select>
                </div>
              </div>

              <div style="display: grid; grid-template-columns: 1.5fr 1fr 1fr; gap: 16px;">
                <div class="form-group">
                  <label class="form-label">Product / Commodity *</label>
                  <select id="product_id" class="form-select" required onchange="DealFormComponent.recalc()">
                    <option value="">-- Select Product / Commodity --</option>
                    ${productOptions}
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">
                    <span>Quantity (Quintals) *</span>
                    <span class="unit-badge">10 Qtl = 1 MT</span>
                  </label>
                  <input type="number" step="0.01" min="0.01" id="quantity_qtl" class="form-control font-mono" placeholder="e.g. 320" required oninput="DealFormComponent.recalc()">
                </div>
                <div class="form-group">
                  <label class="form-label">
                    <span>Rate (₹ / Quintal) *</span>
                    <span class="unit-badge">Per Qtl</span>
                  </label>
                  <input type="number" step="0.01" min="0.01" id="rate_per_qtl" class="form-control font-mono" placeholder="e.g. 15700" required oninput="DealFormComponent.recalc()">
                </div>
              </div>

              <!-- GST & Tax Settings -->
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; background: rgba(0,0,0,0.15); padding: 12px; border-radius: var(--radius-md); margin-bottom: 16px;">
                <div class="form-group" style="margin-bottom: 0;">
                  <label class="form-label">GST Applicability</label>
                  <select id="gst_applicable" class="form-select" onchange="DealFormComponent.recalc()">
                    <option value="1" selected>+ GST Applicable (Standard)</option>
                    <option value="0">GST Exempt / Nil Rate</option>
                  </select>
                </div>
                <div class="form-group" style="margin-bottom: 0;">
                  <label class="form-label">GST Percentage (%)</label>
                  <input type="number" step="0.1" id="gst_pct" class="form-control font-mono" value="5.0" oninput="DealFormComponent.recalc()">
                </div>
              </div>

              <!-- Dual Brokerage Settings -->
              <div style="border-top: 1px solid var(--border-subtle); padding-top: 16px; margin-top: 8px;">
                <h4 style="font-size: 0.875rem; margin-bottom: 12px; color: var(--text-gold);">
                  Dual-Party Brokerage Setup (Calculated Per Metric Tonne)
                </h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                  <div class="form-group">
                    <label class="form-label">
                      <span>Buyer Brokerage (₹ / Tonne)</span>
                      <span class="unit-badge">₹/MT</span>
                    </label>
                    <input type="number" step="0.01" min="0" id="buyer_brokerage_rate" class="form-control font-mono" value="50.0" oninput="DealFormComponent.recalc()">
                  </div>
                  <div class="form-group">
                    <label class="form-label">
                      <span>Seller Brokerage (₹ / Tonne)</span>
                      <span class="unit-badge">₹/MT</span>
                    </label>
                    <input type="number" step="0.01" min="0" id="seller_brokerage_rate" class="form-control font-mono" value="50.0" oninput="DealFormComponent.recalc()">
                  </div>
                </div>

                <div class="form-group">
                  <label class="form-label">Override Reason / Brokerage Notes (Optional)</label>
                  <input type="text" id="brokerage_override_reason" class="form-control" placeholder="Required if rate modified from party master default">
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">Deal Notes & Special Instructions</label>
                <textarea id="notes" class="form-control" rows="2" placeholder="e.g., Payment within 15 days, ex-mill delivery terms"></textarea>
              </div>

              <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px;">
                <button type="button" class="btn btn-secondary" onclick="DealFormComponent.saveAsDraft()">
                  Save as Draft
                </button>
                <button type="submit" class="btn btn-primary">
                  <span>💾</span> Confirm & Create Deal Chain
                </button>
              </div>
            </form>
          </div>

          <!-- Live Financial Calculation Preview -->
          <div>
            <div class="card" style="position: sticky; top: 88px;">
              <div class="card-header">
                <div class="card-title text-gold"><span>⚡</span> Live Deal Preview</div>
              </div>
              
              <div style="display: flex; flex-direction: column; gap: 14px; font-size: 0.875rem;">
                
                <div style="display: flex; justify-content: space-between; padding-bottom: 8px; border-bottom: 1px solid var(--border-subtle);">
                  <span class="text-secondary">Quantity in Tonnes:</span>
                  <span class="font-mono" style="font-weight: 700;" id="prev-tonnes">0.000 MT</span>
                </div>

                <div style="display: flex; justify-content: space-between;">
                  <span class="text-secondary">Taxable Commercial Value:</span>
                  <span class="font-mono" id="prev-taxable">₹0.00</span>
                </div>

                <div style="display: flex; justify-content: space-between;">
                  <span class="text-secondary">Estimated GST:</span>
                  <span class="font-mono" id="prev-gst">₹0.00</span>
                </div>

                <div style="display: flex; justify-content: space-between; padding-bottom: 8px; border-bottom: 1px solid var(--border-subtle);">
                  <span class="text-secondary">Total Goods Value:</span>
                  <span class="font-mono" style="font-weight: 700; color: var(--info-blue);" id="prev-total-goods">₹0.00</span>
                </div>

                <!-- Brokerage breakdown -->
                <div style="background: rgba(0,0,0,0.2); padding: 12px; border-radius: var(--radius-md);">
                  <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-gold); text-transform: uppercase; margin-bottom: 8px;">
                    Brokerage Receivable
                  </div>
                  <div style="display: flex; justify-content: space-between; font-size: 0.8125rem; margin-bottom: 4px;">
                    <span class="text-secondary">Buyer Commission:</span>
                    <span class="font-mono" id="prev-buyer-brok">₹0.00</span>
                  </div>
                  <div style="display: flex; justify-content: space-between; font-size: 0.8125rem; margin-bottom: 6px;">
                    <span class="text-secondary">Seller Commission:</span>
                    <span class="font-mono" id="prev-seller-brok">₹0.00</span>
                  </div>
                  <div style="display: flex; justify-content: space-between; font-size: 0.95rem; font-weight: 700; color: var(--profit-green); border-top: 1px solid var(--border-subtle); padding-top: 6px;">
                    <span>Total Deal Brokerage:</span>
                    <span class="font-mono" id="prev-total-brok">₹0.00</span>
                  </div>
                </div>

                <div id="delivery-warning" style="display: none; background: var(--loss-red-bg); border: 1px solid var(--loss-red-border); color: var(--loss-red); padding: 8px 12px; border-radius: var(--radius-sm); font-size: 0.75rem;">
                  ⚠️ Warning: Target delivery date is earlier than the deal date.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    this.recalc();
  },

  handleBuyerChange() {
    const select = document.getElementById('buyer_id');
    const opt = select.options[select.selectedIndex];
    if (opt && opt.dataset.buyerBrok) {
      document.getElementById('buyer_brokerage_rate').value = opt.dataset.buyerBrok;
    }
    this.recalc();
  },

  handleSellerChange() {
    const select = document.getElementById('seller_id');
    const opt = select.options[select.selectedIndex];
    if (opt && opt.dataset.sellerBrok) {
      document.getElementById('seller_brokerage_rate').value = opt.dataset.sellerBrok;
    }
    this.recalc();
  },

  recalc() {
    const qtl = Number(document.getElementById('quantity_qtl')?.value || 0);
    const tonnes = qtl / 10;
    const rate = Number(document.getElementById('rate_per_qtl')?.value || 0);
    const gstApp = document.getElementById('gst_applicable')?.value === '1';
    const gstPct = Number(document.getElementById('gst_pct')?.value || 5);

    const bBrokRate = Number(document.getElementById('buyer_brokerage_rate')?.value || 0);
    const sBrokRate = Number(document.getElementById('seller_brokerage_rate')?.value || 0);

    const taxable = qtl * rate;
    const gstAmt = gstApp ? taxable * (gstPct / 100) : 0;
    const totalGoods = taxable + gstAmt;

    const bBrokAmt = tonnes * bBrokRate;
    const sBrokAmt = tonnes * sBrokRate;
    const totalBrok = bBrokAmt + sBrokAmt;

    if (document.getElementById('prev-tonnes')) {
      document.getElementById('prev-tonnes').innerText = `${tonnes.toFixed(3)} MT`;
      document.getElementById('prev-taxable').innerText = Store.formatINR(taxable);
      document.getElementById('prev-gst').innerText = Store.formatINR(gstAmt);
      document.getElementById('prev-total-goods').innerText = Store.formatINR(totalGoods);
      document.getElementById('prev-buyer-brok').innerText = Store.formatINR(bBrokAmt);
      document.getElementById('prev-seller-brok').innerText = Store.formatINR(sBrokAmt);
      document.getElementById('prev-total-brok').innerText = Store.formatINR(totalBrok);
    }

    // Delivery date sanity check
    const dDate = document.getElementById('deal_date')?.value;
    const delDate = document.getElementById('delivery_date')?.value;
    const warn = document.getElementById('delivery-warning');
    if (warn && dDate && delDate) {
      warn.style.display = delDate < dDate ? 'block' : 'none';
    }
  },

  async handleSubmit(event, status = 'confirmed') {
    event.preventDefault();

    const buyerId = document.getElementById('buyer_id').value;
    const sellerId = document.getElementById('seller_id').value;
    const productId = document.getElementById('product_id').value;

    if (!productId) {
      Store.showToast('Please select a product / commodity.', 'error');
      return;
    }

    if (!buyerId || !sellerId) {
      Store.showToast('Please select both buyer and seller parties.', 'error');
      return;
    }

    if (buyerId === sellerId) {
      if (!confirm('Buyer and Seller are identical. Are you sure you want to record a self-party transaction?')) {
        return;
      }
    }

    const payload = {
      deal_date: document.getElementById('deal_date').value,
      delivery_date: document.getElementById('delivery_date').value,
      buyer_id: Number(buyerId),
      seller_id: Number(sellerId),
      product_id: Number(document.getElementById('product_id').value),
      quantity_qtl: Number(document.getElementById('quantity_qtl').value),
      rate_per_qtl: Number(document.getElementById('rate_per_qtl').value),
      gst_applicable: document.getElementById('gst_applicable').value === '1',
      gst_pct: Number(document.getElementById('gst_pct').value),
      buyer_brokerage_rate_per_tonne: Number(document.getElementById('buyer_brokerage_rate').value),
      seller_brokerage_rate_per_tonne: Number(document.getElementById('seller_brokerage_rate').value),
      brokerage_override_reason: document.getElementById('brokerage_override_reason').value,
      notes: document.getElementById('notes').value,
      status
    };

    try {
      const res = await API.createDeal(payload);
      if (res.success) {
        Store.showToast(`Deal ${res.deal_number} created successfully!`, 'success');
        App.viewChain(res.chain_id);
      }
    } catch (err) {
      Store.showToast(`Failed to create deal: ${err.message}`, 'error');
    }
  },

  saveAsDraft() {
    // Validate minimally — only dates and status are required for draft
    const buyerId = document.getElementById('buyer_id').value;
    const sellerId = document.getElementById('seller_id').value;
    const productId = document.getElementById('product_id').value;
    const qty = document.getElementById('quantity_qtl').value;
    const rate = document.getElementById('rate_per_qtl').value;

    if (!productId || !buyerId || !sellerId || !qty || !rate) {
      Store.showToast('Please fill in required fields (Product, Buyer, Seller, Quantity, Rate) before saving as draft.', 'error');
      return;
    }

    this.handleSubmit({ preventDefault: () => {} }, 'draft');
  }
};
