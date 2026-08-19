/**
 * Product Master Catalog Component
 */
const ProductMasterComponent = {
  async render(container) {
    container.innerHTML = `
      <div class="animate-fade-in">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
          <div>
            <h1>Product & Commodity Master</h1>
            <p class="text-secondary" style="font-size: 0.875rem;">Edible Oil Catalog, Standard Units, GST Tax Slabs & HSN/SAC Codes</p>
          </div>
          <button class="btn btn-primary" onclick="ProductMasterComponent.openAddProductModal()">
            <span>➕</span> Add New Product
          </button>
        </div>

        <div class="card">
          <div class="table-responsive">
            <table class="data-table" id="products-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Product / Commodity Name</th>
                  <th>Default Unit</th>
                  <th>Unit Conversion</th>
                  <th>Default GST %</th>
                  <th>HSN / SAC</th>
                  <th>BUSY Item Identifier</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr><td colspan="9" style="text-align: center;">Loading product catalog...</td></tr>
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
      const res = await API.getProducts();
      if (!res.success) return;

      Store.setProducts(res.products);
      const tbody = document.querySelector('#products-table tbody');

      if (res.products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No products defined.</td></tr>';
        return;
      }

      tbody.innerHTML = res.products.map(p => `
        <tr>
          <td><span class="badge badge-info font-bold">${p.code}</span></td>
          <td><strong>${p.name}</strong></td>
          <td>${p.default_unit}</td>
          <td><code>10 Quintals = 1 MT</code></td>
          <td class="font-mono">${p.default_gst_pct}%</td>
          <td class="font-mono">${p.hsn_sac || '1514'}</td>
          <td><code>${p.busy_item_id || 'UNMAPPED'}</code></td>
          <td><span class="badge badge-${p.is_active ? 'completed' : 'cancelled'}">${p.is_active ? 'Active' : 'Inactive'}</span></td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-sm btn-secondary" onclick="ProductMasterComponent.openEditProductModal(${p.id})">
                <span>✏️</span> Edit
              </button>
              <button 
                class="btn btn-sm btn-outline-danger" 
                title="Delete Product"
                style="padding: 2px 8px; font-size: 11px; border-color: rgba(239, 68, 68, 0.4); color: var(--danger-red);"
                onclick="ProductMasterComponent.deleteProduct(${p.id}, '${p.name}')"
              >
                🗑️
              </button>
            </div>
          </td>
        </tr>
      `).join('');

    } catch (err) {
      Store.showToast('Error loading products: ' + err.message, 'error');
    }
  },

  async deleteProduct(productId, productName) {
    if (!confirm(`Are you sure you want to delete Product "${productName}"?\n\nIt will be moved to Deleted Items where you can restore it anytime.`)) {
      return;
    }

    try {
      await API.deleteProduct(productId, 'Deleted from product master');
      Store.showToast(`Product "${productName}" deleted.`, 'warning', async () => {
        await API.restoreProduct(productId);
        Store.showToast(`Product "${productName}" restored successfully!`, 'success');
        ProductMasterComponent.loadData();
      });
      this.loadData();
    } catch (err) {
      Store.showToast(`Delete product failed: ${err.message}`, 'error');
    }
  },

  openAddProductModal() {
    const bodyHtml = `
      <form id="product-modal-form" onsubmit="ProductMasterComponent.handleAddProductSubmit(event)">
        <div class="form-group">
          <label class="form-label">Product Name *</label>
          <input type="text" id="pr_name" class="form-control" placeholder="e.g. MUSTARD OIL" required>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Short Code *</label>
            <input type="text" id="pr_code" class="form-control font-mono" placeholder="e.g. M.OIL" required>
          </div>
          <div class="form-group">
            <label class="form-label">Default Unit</label>
            <input type="text" id="pr_unit" class="form-control" value="quintals" readonly>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Default GST %</label>
            <input type="number" step="0.1" id="pr_gst" class="form-control font-mono" value="5.0" required>
          </div>
          <div class="form-group">
            <label class="form-label">HSN / SAC Code</label>
            <input type="text" id="pr_hsn" class="form-control font-mono" value="1514">
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">BUSY Item Identifier (Optional)</label>
          <input type="text" id="pr_busy" class="form-control" placeholder="e.g. BUSY_ITM_MOIL">
        </div>
      </form>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="Store.closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="document.getElementById('product-modal-form').requestSubmit()">
        <span>💾</span> Save Product
      </button>
    `;

    Store.openModal('Add New Commodity / Product', bodyHtml, footerHtml);
  },

  async handleAddProductSubmit(event) {
    event.preventDefault();
    const payload = {
      name: document.getElementById('pr_name').value,
      code: document.getElementById('pr_code').value,
      default_unit: document.getElementById('pr_unit').value,
      default_gst_pct: Number(document.getElementById('pr_gst').value),
      hsn_sac: document.getElementById('pr_hsn').value,
      busy_item_id: document.getElementById('pr_busy').value
    };

    try {
      const res = await API.createProduct(payload);
      if (res.success) {
        Store.closeModal();
        Store.showToast('Product added to catalog!', 'success');
        this.loadData();
      }
    } catch (err) {
      Store.showToast('Failed to add product: ' + err.message, 'error');
    }
  },

  openEditProductModal(productId) {
    const prod = (Store.state.products || []).find(p => p.id === productId);
    if (!prod) return;

    const bodyHtml = `
      <form id="edit-product-modal-form" onsubmit="ProductMasterComponent.handleEditProductSubmit(event, ${productId})">
        <div class="form-group">
          <label class="form-label">Product Name *</label>
          <input type="text" id="epr_name" class="form-control" value="${prod.name}" required>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">Short Code *</label>
            <input type="text" id="epr_code" class="form-control font-mono" value="${prod.code}" required>
          </div>
          <div class="form-group">
            <label class="form-label">Default GST %</label>
            <input type="number" step="0.1" id="epr_gst" class="form-control font-mono" value="${prod.default_gst_pct}" required>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label">HSN / SAC Code</label>
            <input type="text" id="epr_hsn" class="form-control font-mono" value="${prod.hsn_sac || '1514'}">
          </div>
          <div class="form-group">
            <label class="form-label">BUSY Item Identifier</label>
            <input type="text" id="epr_busy" class="form-control" value="${prod.busy_item_id || ''}">
          </div>
        </div>
      </form>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="Store.closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="document.getElementById('edit-product-modal-form').requestSubmit()">
        <span>💾</span> Update Product
      </button>
    `;

    Store.openModal(`Edit Product: ${prod.name}`, bodyHtml, footerHtml);
  },

  async handleEditProductSubmit(event, productId) {
    event.preventDefault();
    const payload = {
      name: document.getElementById('epr_name').value,
      code: document.getElementById('epr_code').value,
      default_gst_pct: Number(document.getElementById('epr_gst').value),
      hsn_sac: document.getElementById('epr_hsn').value,
      busy_item_id: document.getElementById('epr_busy').value
    };

    try {
      const res = await API.updateProduct(productId, payload);
      if (res.success) {
        Store.closeModal();
        Store.showToast('Product updated successfully!', 'success');
        this.loadData();
      }
    } catch (err) {
      Store.showToast('Failed to update product: ' + err.message, 'error');
    }
  }
};
