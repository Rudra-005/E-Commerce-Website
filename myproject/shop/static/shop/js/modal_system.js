/**
 * Professional Bootstrap-Style Modal System
 * Provides reusable functions for alerts, confirms, prompts, toasts, and custom forms.
 */

window.ModalSystem = {
    modalEl: null,
    backdropEl: null,
    titleEl: null,
    bodyEl: null,
    footerEl: null,
    closeBtnEl: null,
    toastContainer: null,
    resolvePromise: null,

    init() {
        this.modalEl = document.getElementById('bsReusableModal');
        this.backdropEl = document.getElementById('bsModalBackdrop');
        this.titleEl = document.getElementById('bsModalTitle');
        this.bodyEl = document.getElementById('bsModalBody');
        this.footerEl = document.getElementById('bsModalFooter');
        this.closeBtnEl = document.getElementById('bsModalCloseBtn');
        this.toastContainer = document.getElementById('bsToastContainer');

        if (this.closeBtnEl) {
            this.closeBtnEl.addEventListener('click', () => this.hide());
        }

        // Close on ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modalEl && this.modalEl.classList.contains('show')) {
                this.hide();
                if (this.resolvePromise) this.resolvePromise(null);
            }
        });
    },

    show() {
        if (!this.modalEl) this.init();
        this.backdropEl.classList.add('show');
        this.modalEl.classList.add('show');
        this.modalEl.setAttribute('aria-hidden', 'false');
        this.modalEl.focus();
    },

    hide() {
        if (this.modalEl) {
            this.modalEl.classList.remove('show');
            this.backdropEl.classList.remove('show');
            this.modalEl.setAttribute('aria-hidden', 'true');
        }
    },

    /**
     * Alert Modal
     */
    showAlert(message, title = 'Notification') {
        if (!this.modalEl) this.init();
        return new Promise((resolve) => {
            this.titleEl.innerText = title;
            this.bodyEl.innerHTML = `<p>${message}</p>`;
            this.footerEl.innerHTML = `<button type="button" class="bs-btn bs-btn-primary" id="bsModalOkBtn">OK</button>`;
            
            this.show();
            this.resolvePromise = resolve;

            document.getElementById('bsModalOkBtn').addEventListener('click', () => {
                this.hide();
                resolve(true);
            });
            
            setTimeout(() => document.getElementById('bsModalOkBtn').focus(), 100);
        });
    },

    /**
     * Confirm Modal
     */
    showConfirm(message, title = 'Confirm Action') {
        if (!this.modalEl) this.init();
        return new Promise((resolve) => {
            this.titleEl.innerText = title;
            this.bodyEl.innerHTML = `<p>${message}</p>`;
            this.footerEl.innerHTML = `
                <button type="button" class="bs-btn bs-btn-secondary" id="bsModalCancelBtn">Cancel</button>
                <button type="button" class="bs-btn bs-btn-danger" id="bsModalConfirmBtn">Confirm</button>
            `;
            
            this.show();
            this.resolvePromise = resolve;

            document.getElementById('bsModalCancelBtn').addEventListener('click', () => {
                this.hide();
                resolve(false);
            });
            document.getElementById('bsModalConfirmBtn').addEventListener('click', () => {
                this.hide();
                resolve(true);
            });
            
            setTimeout(() => document.getElementById('bsModalCancelBtn').focus(), 100);
        });
    },

    /**
     * Input Modal (Prompt replacement)
     */
    showInput(message, title = 'Input Required', inputType = 'text') {
        if (!this.modalEl) this.init();
        return new Promise((resolve) => {
            this.titleEl.innerText = title;
            this.bodyEl.innerHTML = `
                <label class="bs-form-label">${message}</label>
                <input type="${inputType}" class="bs-form-control" id="bsModalInput">
            `;
            this.footerEl.innerHTML = `
                <button type="button" class="bs-btn bs-btn-secondary" id="bsModalCancelBtn">Cancel</button>
                <button type="button" class="bs-btn bs-btn-primary" id="bsModalSubmitBtn">Submit</button>
            `;
            
            this.show();
            this.resolvePromise = resolve;
            
            const inputEl = document.getElementById('bsModalInput');

            document.getElementById('bsModalCancelBtn').addEventListener('click', () => {
                this.hide();
                resolve(null);
            });
            document.getElementById('bsModalSubmitBtn').addEventListener('click', () => {
                this.hide();
                resolve(inputEl.value);
            });
            
            setTimeout(() => inputEl.focus(), 100);
        });
    },

    /**
     * Specialized Rejection Modal for Admins
     */
    showRejectionModal(id, actionUrl, csrfToken) {
        if (!this.modalEl) this.init();
        return new Promise((resolve) => {
            this.titleEl.innerText = 'Reject Cancellation Request';
            this.bodyEl.innerHTML = `
                <div style="margin-bottom: 1rem;">
                    <label class="bs-form-label">Reason *</label>
                    <textarea class="bs-form-control" id="rejectionReason" rows="3" placeholder="Enter rejection reason..." maxlength="300" required></textarea>
                    <div style="display: flex; justify-content: space-between; font-size: 0.85em; color: #6c757d; margin-top: 5px;">
                        <span>Maximum 300 characters</span>
                        <span id="rejectionCharCount">0 / 300</span>
                    </div>
                    <div class="bs-invalid-feedback" id="rejectionReasonError">Reason is required.</div>
                </div>
                <div>
                    <label class="bs-form-label">Optional Notes</label>
                    <textarea class="bs-form-control" id="rejectionNotes" rows="2" placeholder="Additional notes..."></textarea>
                </div>
            `;
            this.footerEl.innerHTML = `
                <button type="button" class="bs-btn bs-btn-secondary" id="bsModalCancelBtn">Cancel</button>
                <button type="button" class="bs-btn bs-btn-danger" id="bsModalSubmitBtn" disabled>Reject Request</button>
            `;
            
            this.show();
            
            const reasonEl = document.getElementById('rejectionReason');
            const notesEl = document.getElementById('rejectionNotes');
            const countEl = document.getElementById('rejectionCharCount');
            const submitBtn = document.getElementById('bsModalSubmitBtn');
            const cancelBtn = document.getElementById('bsModalCancelBtn');
            const errorEl = document.getElementById('rejectionReasonError');

            reasonEl.addEventListener('input', () => {
                countEl.innerText = `${reasonEl.value.length} / 300`;
                if (reasonEl.value.trim().length > 0) {
                    submitBtn.disabled = false;
                    reasonEl.classList.remove('is-invalid');
                } else {
                    submitBtn.disabled = true;
                }
            });

            cancelBtn.addEventListener('click', () => {
                this.hide();
                resolve(false);
            });

            submitBtn.addEventListener('click', async () => {
                const reason = reasonEl.value.trim();
                if (!reason) {
                    reasonEl.classList.add('is-invalid');
                    return;
                }

                // Show loading
                submitBtn.disabled = true;
                const originalText = submitBtn.innerText;
                submitBtn.innerHTML = `<span class="bs-spinner-border bs-spinner-border-sm" role="status" aria-hidden="true"></span> Rejecting...`;

                // The existing backend only accepts 'notes' for rejection reason in processCancellation
                // We will combine them or just pass it as notes
                const combinedNotes = `Reason: ${reason}\nNotes: ${notesEl.value.trim()}`;

                try {
                    const res = await fetch(actionUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({ action: 'reject', notes: combinedNotes })
                    });
                    
                    const data = await res.json();
                    if (data.success) {
                        this.hide();
                        this.showToast('✓ Cancellation request rejected successfully.', 'success');
                        resolve(true); // Let the caller know it succeeded (can reload or update DOM)
                    } else {
                        reasonEl.classList.add('is-invalid');
                        errorEl.innerText = data.error || 'Server validation failed.';
                        submitBtn.disabled = false;
                        submitBtn.innerText = originalText;
                    }
                } catch(err) {
                    reasonEl.classList.add('is-invalid');
                    errorEl.innerText = 'Network error occurred.';
                    submitBtn.disabled = false;
                    submitBtn.innerText = originalText;
                }
            });
        });
    },

    /**
     * Bootstrap Toast
     */
    showToast(message, type = 'success') {
        if (!this.toastContainer) this.init();
        
        const toastId = 'toast-' + Math.random().toString(36).substr(2, 9);
        const headerClass = type === 'success' ? 'bs-toast-success' : 'bs-toast-danger';
        const title = type === 'success' ? 'Success' : 'Error';
        const icon = type === 'success' ? '✓' : '⚠️';

        const toastHtml = `
            <div id="${toastId}" class="bs-toast ${headerClass}" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="bs-toast-header">
                    <strong style="margin-right: auto;">${icon} ${title}</strong>
                    <button type="button" class="bs-btn-close" onclick="document.getElementById('${toastId}').classList.remove('show'); setTimeout(()=>document.getElementById('${toastId}').remove(), 300)" aria-label="Close"></button>
                </div>
                <div class="bs-toast-body">
                    ${message}
                </div>
            </div>
        `;

        this.toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastEl = document.getElementById(toastId);
        // Trigger reflow for animation
        void toastEl.offsetWidth;
        toastEl.classList.add('show');

        setTimeout(() => {
            if (toastEl) {
                toastEl.classList.remove('show');
                setTimeout(() => toastEl.remove(), 300);
            }
        }, 4000);
    }
};

// Global aliases to replace standard functions
window.showCustomAlert = (msg, title) => window.ModalSystem.showAlert(msg, title);
window.showCustomConfirm = (msg, title) => window.ModalSystem.showConfirm(msg, title);
window.showCustomPrompt = (msg, title, type) => window.ModalSystem.showInput(msg, title, type);
window.showCustomToast = (msg, type) => window.ModalSystem.showToast(msg, type);

document.addEventListener('DOMContentLoaded', () => {
    window.ModalSystem.init();
});
