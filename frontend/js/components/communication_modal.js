/**
 * Zero-Cost WhatsApp & Email Communication Modal Component
 * Uses wa.me click-to-chat and mailto: URI schemes (Strict Zero API Cost)
 */
const CommModalComponent = {
  activeDraft: null,
  currentParams: null,

  /**
   * Opens the communication composer & preview modal.
   * @param {Object} params - { message_type, party_id, deal_id, chain_id, options }
   */
  async open(params = {}) {
    this.currentParams = params || {};
    try {
      Store.showToast('Preparing communication draft...', 'info');
      const res = await API.prepareCommunication(this.currentParams);
      if (!res || !res.success) {
        Store.showToast('Error: ' + ((res && res.error) || 'Failed to prepare draft'), 'error');
        return;
      }

      this.activeDraft = res.draft;
      this.renderModal();
    } catch (err) {
      console.error('Error preparing communication message:', err);
      Store.showToast('Error preparing message: ' + (err.message || err), 'error');
    }
  },

  renderModal() {
    const existing = document.getElementById('comm-modal-overlay');
    if (existing) existing.remove();

    const d = this.activeDraft;
    const allParties = d.all_parties || Store.state.parties || [];
    const partyOptions = allParties.map(p => `
      <option value="${p.id}" ${p.id === d.party_id ? 'selected' : ''}>${p.name}</option>
    `).join('');

    const whatsappOptions = (d.whatsapp_candidates || []).map(c => `
      <option value="${c.value}">${c.label}</option>
    `).join('');

    const emailOptions = (d.email_candidates || []).map(c => `
      <option value="${c.value}">${c.label}</option>
    `).join('');

    const isBothPreferred = d.preferred_method === 'both' && (d.whatsapp_candidates || []).length > 0 && (d.email_candidates || []).length > 0;

    const modalHtml = `
      <div id="comm-modal-overlay" class="modal-overlay active" style="
        position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 99999;
        display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px);
        padding: 16px;
      ">
        <div class="card animate-fade-in modal-container" style="
          width: 100%; max-width: 780px; max-height: 94vh; overflow-y: auto;
          background: #1e293b; border: 1px solid var(--border-subtle); box-shadow: 0 24px 48px rgba(0,0,0,0.6);
          position: relative; padding: 20px;
        ">
          <!-- Modal Header -->
          <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px; margin-bottom: 14px;">
            <div>
              <h3 style="display: flex; align-items: center; gap: 8px; color: var(--text-gold); margin: 0; font-size: 1.15rem;">
                <span>💬</span> Free One-Click Client Communication
              </h3>
              <p class="text-secondary" style="font-size: 0.75rem; margin-top: 4px; margin-bottom: 0;">
                Target: <strong id="comm-target-party-label">${d.party_name}</strong> (Attn: ${d.contact_person}) | Channel: <span class="badge badge-info" style="font-size: 0.65rem;">${(d.preferred_method || 'both').toUpperCase()}</span>
              </p>
            </div>
            <button class="btn btn-sm btn-secondary" onclick="CommModalComponent.close()" style="font-size: 1.1rem; padding: 2px 8px; line-height: 1;">
              ✕
            </button>
          </div>

          <!-- Configuration Grid: Party, Action, Phone, Email -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; background: rgba(0,0,0,0.25); padding: 12px; border-radius: var(--radius-md);">
            <div class="form-group" style="margin-bottom: 0;">
              <label class="form-label" style="font-size: 0.75rem;">🏢 Select Target Party</label>
              <select id="comm-party-select" class="form-select form-select-sm" style="font-size: 0.75rem;" onchange="CommModalComponent.switchParty(this.value)">
                ${partyOptions || `<option value="${d.party_id}">${d.party_name}</option>`}
              </select>
            </div>

            <div class="form-group" style="margin-bottom: 0;">
              <label class="form-label" style="font-size: 0.75rem;">📋 Message Action</label>
              <select id="comm-template-select" class="form-select form-select-sm" style="font-size: 0.75rem;" onchange="CommModalComponent.switchTemplate(this.value)">
                <option value="deal_confirmation_buyer" ${d.message_type === 'deal_confirmation_buyer' ? 'selected' : ''}>Send Deal Confirmation to Buyer</option>
                <option value="deal_confirmation_seller" ${d.message_type === 'deal_confirmation_seller' ? 'selected' : ''}>Send Deal Confirmation to Seller</option>
                <option value="final_billing_instruction" ${d.message_type === 'final_billing_instruction' ? 'selected' : ''}>Send Final Billing Instruction</option>
                <option value="delivery_reminder" ${d.message_type === 'delivery_reminder' ? 'selected' : ''}>Send Delivery Reminder</option>
                <option value="rate_confirmation" ${d.message_type === 'rate_confirmation' ? 'selected' : ''}>Send Rate Confirmation</option>
                <option value="deal_amendment" ${d.message_type === 'deal_amendment' ? 'selected' : ''}>Send Deal Amendment</option>
                <option value="deal_cancellation" ${d.message_type === 'deal_cancellation' ? 'selected' : ''}>Send Deal Cancellation</option>
                <option value="brokerage_statement" ${d.message_type === 'brokerage_statement' ? 'selected' : ''}>Send Brokerage Statement</option>
                <option value="brokerage_payment_reminder" ${d.message_type === 'brokerage_payment_reminder' ? 'selected' : ''}>Send Brokerage Payment Reminder</option>
                <option value="custom_message" ${d.message_type === 'custom_message' ? 'selected' : ''}>Send Custom Message</option>
              </select>
            </div>

            <div class="form-group" style="margin-bottom: 0;">
              <label class="form-label" style="font-size: 0.75rem; display: flex; justify-content: space-between;">
                <span>📱 WhatsApp Number</span>
                <span class="text-muted font-mono" style="font-size: 0.65rem;">91XXXXXXXXXX</span>
              </label>
              <div style="display: flex; gap: 4px;">
                <select id="comm-recipient-phone" class="form-select form-select-sm font-mono" style="font-size: 0.75rem; flex: 1;" onchange="CommModalComponent.syncPhoneCustom(this.value)">
                  ${whatsappOptions || '<option value="">No phone number saved</option>'}
                </select>
                <input type="text" id="comm-custom-phone" class="form-control form-control-sm font-mono" placeholder="Direct 91..." style="font-size: 0.75rem; width: 110px;" value="${(d.whatsapp_candidates && d.whatsapp_candidates[0]) ? d.whatsapp_candidates[0].value : ''}">
              </div>
            </div>

            <div class="form-group" style="margin-bottom: 0;">
              <label class="form-label" style="font-size: 0.75rem; display: flex; justify-content: space-between;">
                <span>✉️ Recipient Email</span>
                <span class="text-muted" style="font-size: 0.65rem;">Verified</span>
              </label>
              <div style="display: flex; gap: 4px;">
                <select id="comm-recipient-email" class="form-select form-select-sm" style="font-size: 0.75rem; flex: 1;" onchange="CommModalComponent.syncEmailCustom(this.value)">
                  ${emailOptions || '<option value="">No email address saved</option>'}
                </select>
                <input type="email" id="comm-custom-email" class="form-control form-control-sm" placeholder="Direct email..." style="font-size: 0.75rem; width: 140px;" value="${(d.email_candidates && d.email_candidates[0]) ? d.email_candidates[0].value : ''}">
              </div>
            </div>
          </div>

          <!-- Privacy & Content Options -->
          <div style="background: rgba(245, 158, 11, 0.06); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: var(--radius-md); padding: 8px 12px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-size: 0.75rem; font-weight: 700; color: var(--text-gold); text-transform: uppercase;">
                🔒 Financial Privacy & Content Safeguards
              </span>
              <span class="badge badge-profit" style="font-size: 0.65rem;">Internal Margin Excluded</span>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.75rem;">
              <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
                <input type="checkbox" id="comm-opt-rate" checked onchange="CommModalComponent.recalcDraft()">
                <span>Include Rate & GST</span>
              </label>
              <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
                <input type="checkbox" id="comm-opt-total" checked onchange="CommModalComponent.recalcDraft()">
                <span>Include Total Approximate Value</span>
              </label>
              <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
                <input type="checkbox" id="comm-opt-brokerage" onchange="CommModalComponent.recalcDraft()">
                <span style="color: #fca5a5;">Include Brokerage (Confidential)</span>
              </label>
            </div>
          </div>

          <!-- Email Subject & CC/BCC (Collapsible) -->
          <div class="form-group" style="margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <label class="form-label" style="font-size: 0.75rem; margin-bottom: 0;">Email Subject</label>
              <a href="#" onclick="CommModalComponent.toggleCcBcc(); return false;" style="font-size: 0.7rem; color: var(--info-blue);">
                + Add CC / BCC
              </a>
            </div>
            <input type="text" id="comm-subject" class="form-control form-control-sm" value="${d.subject}" style="font-size: 0.8125rem;">
          </div>

          <div id="comm-cc-bcc-box" style="display: none; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px;">
            <div class="form-group" style="margin-bottom: 0;">
              <label class="form-label" style="font-size: 0.7rem;">CC Email</label>
              <input type="email" id="comm-cc" class="form-control form-control-sm" placeholder="cc@example.com" style="font-size: 0.75rem;">
            </div>
            <div class="form-group" style="margin-bottom: 0;">
              <label class="form-label" style="font-size: 0.7rem;">BCC Email</label>
              <input type="email" id="comm-bcc" class="form-control form-control-sm" placeholder="bcc@example.com" style="font-size: 0.75rem;">
            </div>
          </div>

          <!-- Message Body Editor -->
          <div class="form-group" style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <label class="form-label" style="font-size: 0.75rem; margin-bottom: 0;">Message Draft (Editable)</label>
              <span class="text-muted" style="font-size: 0.7rem;" id="comm-char-count">Live Preview</span>
            </div>
            <textarea id="comm-body" class="form-control font-mono" rows="8" style="font-size: 0.8125rem; line-height: 1.45; white-space: pre-wrap;">${d.body}</textarea>
          </div>

          <!-- Fallback Copy & Download Toolbar -->
          <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-subtle); padding: 6px 10px; border-radius: var(--radius-md); margin-bottom: 14px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: space-between;">
            <span style="font-size: 0.7rem; color: var(--text-muted); font-weight: 600;">📋 Fallback Actions:</span>
            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
              <button class="btn btn-sm btn-glass-default" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.copyRecipient()">
                Copy Recipient
              </button>
              <button class="btn btn-sm btn-glass-default" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.copySubject()">
                Copy Subject
              </button>
              <button class="btn btn-sm btn-glass-default" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.copyBody()">
                Copy Message
              </button>
              <button class="btn btn-sm btn-glass-default" style="font-size: 0.7rem; padding: 2px 7px; color: var(--text-gold);" onclick="CommModalComponent.downloadDealPdf()">
                📥 Download Deal PDF
              </button>
              <button class="btn btn-sm btn-glass-default" style="font-size: 0.7rem; padding: 2px 7px;" onclick="CommModalComponent.openRediffmail()">
                🌐 Rediffmail Login
              </button>
            </div>
          </div>

          <!-- Send using Actions -->
          <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 10px; border-top: 1px solid var(--border-subtle);">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary);">Send using:</span>
            </div>

            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button class="btn btn-glass-default btn-sm" onclick="CommModalComponent.close()">
                Cancel
              </button>

              ${isBothPreferred ? `
                <button class="btn btn-sm btn-glass-primary" onclick="CommModalComponent.launchBoth()">
                  <span>🚀</span> Open WhatsApp and Email
                </button>
              ` : ''}

              <button class="btn btn-sm btn-glass-success" onclick="CommModalComponent.launchWhatsApp()">
                <span>💬</span> WhatsApp
              </button>

              <button class="btn btn-sm btn-glass-gold" onclick="CommModalComponent.launchEmail()">
                <span>✉️</span> Email
              </button>
            </div>
          </div>

        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
  },

  close() {
    const el = document.getElementById('comm-modal-overlay');
    if (el) el.remove();
  },

  syncPhoneCustom(val) {
    const custom = document.getElementById('comm-custom-phone');
    if (custom && val) custom.value = val;
  },

  syncEmailCustom(val) {
    const custom = document.getElementById('comm-custom-email');
    if (custom && val) custom.value = val;
  },

  toggleCcBcc() {
    const box = document.getElementById('comm-cc-bcc-box');
    if (box) {
      box.style.display = box.style.display === 'none' ? 'grid' : 'none';
    }
  },

  async switchParty(partyId) {
    this.currentParams.party_id = parseInt(partyId);
    await this.recalcDraft();
  },

  async switchTemplate(newType) {
    this.currentParams.message_type = newType;
    await this.recalcDraft();
  },

  async recalcDraft() {
    const includeRate = document.getElementById('comm-opt-rate')?.checked ?? true;
    const includeTotal = document.getElementById('comm-opt-total')?.checked ?? true;
    const includeBrokerage = document.getElementById('comm-opt-brokerage')?.checked ?? false;

    if (includeBrokerage) {
      if (!confirm('⚠️ Notice: Brokerage is confidential. Are you sure you want to include brokerage commissions in this client message?')) {
        document.getElementById('comm-opt-brokerage').checked = false;
        return;
      }
    }

    const updatedParams = {
      ...this.currentParams,
      party_id: parseInt(document.getElementById('comm-party-select')?.value) || this.currentParams.party_id,
      message_type: document.getElementById('comm-template-select')?.value || this.currentParams.message_type,
      options: {
        ...(this.currentParams.options || {}),
        include_rate: includeRate,
        include_total: includeTotal,
        include_brokerage: includeBrokerage
      }
    };

    try {
      const res = await API.prepareCommunication(updatedParams);
      if (res && res.success) {
        this.activeDraft = res.draft;
        const subjEl = document.getElementById('comm-subject');
        const bodyEl = document.getElementById('comm-body');
        const partyLabel = document.getElementById('comm-target-party-label');
        if (subjEl) subjEl.value = res.draft.subject;
        if (bodyEl) bodyEl.value = res.draft.body;
        if (partyLabel) partyLabel.innerText = res.draft.party_name;

        // Update candidate dropdowns
        const phoneSel = document.getElementById('comm-recipient-phone');
        if (phoneSel && res.draft.whatsapp_candidates) {
          phoneSel.innerHTML = res.draft.whatsapp_candidates.map(c => `<option value="${c.value}">${c.label}</option>`).join('') || '<option value="">No phone number saved</option>';
          if (res.draft.whatsapp_candidates[0]) {
            document.getElementById('comm-custom-phone').value = res.draft.whatsapp_candidates[0].value;
          }
        }

        const emailSel = document.getElementById('comm-recipient-email');
        if (emailSel && res.draft.email_candidates) {
          emailSel.innerHTML = res.draft.email_candidates.map(c => `<option value="${c.value}">${c.label}</option>`).join('') || '<option value="">No email address saved</option>';
          if (res.draft.email_candidates[0]) {
            document.getElementById('comm-custom-email').value = res.draft.email_candidates[0].value;
          }
        }
      }
    } catch (err) {
      console.error('Error recalculating draft:', err);
    }
  },

  /**
   * One-click WhatsApp implementation
   */
  async launchWhatsApp() {
    const customPhone = document.getElementById('comm-custom-phone')?.value?.trim();
    const selectPhone = document.getElementById('comm-recipient-phone')?.value?.trim();
    const phoneNumber = customPhone || selectPhone || '';
    const message = document.getElementById('comm-body')?.value || '';

    if (!phoneNumber) {
      Store.showToast('Please enter or select a valid WhatsApp phone number for this party.', 'error');
      return;
    }

    try {
      // 1. Generate WhatsApp click-to-chat link
      const phone = phoneNumber.replace(/\D/g, "");
      if (!phone) {
        throw new Error("A valid WhatsApp number is required (91XXXXXXXXXX).");
      }

      const whatsappUrl = `https://wa.me/${phone}?text=${encodeURIComponent(message)}`;
      window.open(whatsappUrl, "_blank", "noopener,noreferrer");

      // 2. Log communication in backend as 'WhatsApp opened'
      await API.logCommunication({
        channel: 'whatsapp',
        party_id: this.activeDraft.party_id,
        party_name: this.activeDraft.party_name,
        contact_person: this.activeDraft.contact_person,
        recipient_contact: phone,
        deal_id: this.currentParams.deal_id,
        chain_id: this.currentParams.chain_id,
        message_type: this.activeDraft.message_type,
        subject: document.getElementById('comm-subject')?.value || this.activeDraft.subject,
        message_body: message,
        status: 'WhatsApp opened'
      });

      Store.showToast('💬 Opened in WhatsApp. Please manually press Send in WhatsApp.', 'success');
      this.close();
    } catch (err) {
      Store.showToast('Failed to open WhatsApp: ' + err.message, 'error');
    }
  },

  /**
   * One-click email implementation
   */
  async launchEmail() {
    const customEmail = document.getElementById('comm-custom-email')?.value?.trim();
    const selectEmail = document.getElementById('comm-recipient-email')?.value?.trim();
    const recipient = customEmail || selectEmail || '';
    const subject = document.getElementById('comm-subject')?.value || this.activeDraft.subject;
    const body = document.getElementById('comm-body')?.value || this.activeDraft.body;
    const cc = (document.getElementById('comm-cc')?.value || '').trim();
    const bcc = (document.getElementById('comm-bcc')?.value || '').trim();

    if (!recipient) {
      Store.showToast('Please enter or select a valid recipient email address.', 'error');
      return;
    }

    try {
      // 1. Generate standard mailto: link
      const parameters = new URLSearchParams();
      parameters.set("subject", subject);
      parameters.set("body", body);
      if (cc) parameters.set("cc", cc);
      if (bcc) parameters.set("bcc", bcc);

      window.location.href = `mailto:${encodeURIComponent(recipient)}?${parameters.toString()}`;

      // 2. Log communication in backend as 'Email draft opened'
      await API.logCommunication({
        channel: 'email',
        party_id: this.activeDraft.party_id,
        party_name: this.activeDraft.party_name,
        contact_person: this.activeDraft.contact_person,
        recipient_contact: recipient,
        cc: cc || null,
        bcc: bcc || null,
        deal_id: this.currentParams.deal_id,
        chain_id: this.currentParams.chain_id,
        message_type: this.activeDraft.message_type,
        subject: subject,
        message_body: body,
        status: 'Email draft opened'
      });

      Store.showToast('✉️ Email draft opened. Please review and manually press Send.', 'success');
      this.close();
    } catch (err) {
      Store.showToast('Failed to open email draft: ' + err.message, 'error');
    }
  },

  /**
   * Open both WhatsApp and Email separately
   */
  async launchBoth() {
    await this.launchWhatsApp();
    setTimeout(() => {
      this.launchEmail();
    }, 600);
  },

  // Fallback Copy & Download Methods
  copyToClipboard(text, successMsg) {
    if (!text) return;
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(() => {
        Store.showToast(successMsg, 'success');
      }).catch(() => {
        this.fallbackCopy(text, successMsg);
      });
    } else {
      this.fallbackCopy(text, successMsg);
    }
  },

  fallbackCopy(text, successMsg) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    textArea.style.top = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      Store.showToast(successMsg, 'success');
    } catch (err) {
      Store.showToast('Could not copy automatically: ' + err.message, 'error');
    }
    document.body.removeChild(textArea);
  },

  copyRecipient() {
    const phone = document.getElementById('comm-custom-phone')?.value || document.getElementById('comm-recipient-phone')?.value;
    const email = document.getElementById('comm-custom-email')?.value || document.getElementById('comm-recipient-email')?.value;
    const text = phone || email || '';
    if (text) {
      this.copyToClipboard(text, `Copied recipient: ${text}`);
    } else {
      Store.showToast('No recipient contact to copy.', 'error');
    }
  },

  copySubject() {
    const subj = document.getElementById('comm-subject')?.value || this.activeDraft?.subject || '';
    if (subj) {
      this.copyToClipboard(subj, 'Copied email subject!');
    }
  },

  copyBody() {
    const body = document.getElementById('comm-body')?.value || this.activeDraft?.body || '';
    if (body) {
      this.copyToClipboard(body, 'Copied message body!');
    }
  },

  downloadDealPdf() {
    const d = this.activeDraft;
    const subject = document.getElementById('comm-subject')?.value || d.subject;
    const body = document.getElementById('comm-body')?.value || d.body;

    const printHtml = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>${subject}</title>
        <style>
          body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #111; }
          .header { border-bottom: 2px solid #b45309; padding-bottom: 12px; margin-bottom: 20px; }
          .title { font-size: 20px; font-weight: bold; color: #b45309; }
          .meta { font-size: 12px; color: #666; margin-top: 4px; }
          .content { white-space: pre-wrap; font-size: 14px; line-height: 1.6; background: #f8fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 8px; }
          .footer { margin-top: 30px; font-size: 11px; color: #888; border-top: 1px solid #ddd; padding-top: 8px; }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="title">G&C – Ganesh & Company</div>
          <div class="meta">Central Deal & Brokerage Automation | Official Confirmation Slip</div>
        </div>
        <div style="margin-bottom: 16px; font-size: 16px; font-weight: 600;">${subject}</div>
        <div class="content">${body}</div>
        <div class="footer">
          Generated automatically by G&C Central Deal and Brokerage Platform on ${new Date().toLocaleString('en-IN')}.
        </div>
        <script>
          window.print();
        </script>
      </body>
      </html>
    `;

    const printWin = window.open('', '_blank');
    if (printWin) {
      printWin.document.open();
      printWin.document.write(printHtml);
      printWin.document.close();
      Store.showToast('Opened printable Deal Confirmation PDF / Slip!', 'success');
    }
  },

  openRediffmail() {
    window.open('https://mail.rediff.com', '_blank', 'noopener,noreferrer');
  }
};

window.CommModalComponent = CommModalComponent;
