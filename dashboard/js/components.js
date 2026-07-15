/* ==========================================================================
   CUSTODY — UI component helpers
   ========================================================================== */

const UI = (() => {
  let toastRoot = null;

  function ensureToastRoot() {
    if (!toastRoot) {
      toastRoot = document.createElement('div');
      toastRoot.className = 'toast-stack';
      document.body.appendChild(toastRoot);
    }
    return toastRoot;
  }

  function toast(message, type = 'info', ms = 4200) {
    const root = ensureToastRoot();
    const el = document.createElement('div');
    el.className = `toast toast-${type === 'info' ? 'default' : type}`;
    el.innerHTML = `<span>${escapeHtml(message)}</span>`;
    root.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.2s ease';
      setTimeout(() => el.remove(), 200);
    }, ms);
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  }

  function formatBytes(bytes) {
    if (bytes === 0 || bytes == null) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
  }

  function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  function timeAgo(iso) {
    if (!iso) return '—';
    const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  function truncHash(hash, len = 10) {
    if (!hash) return '—';
    return `${hash.slice(0, len)}…${hash.slice(-4)}`;
  }

  function initials(name) {
    if (!name) return '?';
    return name.slice(0, 2).toUpperCase();
  }

  /** Maps a domain status string to a badge visual class. */
  const STATUS_MAP = {
    ONLINE: 'verify', SECURE: 'verify', CLEAN: 'verify', APPROVED: 'verify', COMPLETED: 'verify', RELEASED: 'verify', SUCCESS: 'verify',
    DEGRADED: 'warn', PENDING: 'warn', SUSPICIOUS: 'warn', WARNING: 'warn', ISOLATED: 'warn',
    OFFLINE: 'critical', MALICIOUS: 'critical', REJECTED: 'critical', FAILED: 'critical', DELETED: 'critical', LOCKED: 'critical',
  };

  function badge(status, label) {
    const cls = STATUS_MAP[String(status).toUpperCase()] || 'neutral';
    return `<span class="badge badge-${cls}">${escapeHtml(label || status)}</span>`;
  }

  function skeleton(colspan, rows = 3) {
    return Array.from({ length: rows }).map(() =>
      `<tr class="empty-row"><td colspan="${colspan}"><span class="spinner"></span></td></tr>`
    ).join('');
  }

  function emptyRow(colspan, message) {
    return `<tr class="empty-row"><td colspan="${colspan}">${escapeHtml(message)}</td></tr>`;
  }

  function lockedPanel(message) {
    return `<div class="locked-panel">🔒 ${escapeHtml(message || 'You do not have permission to view this section.')}</div>`;
  }

  // --- Modal ---
  function openModal({ title, bodyHtml, onMount, footerHtml }) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}">
        <div class="modal-header">
          <h3>${escapeHtml(title)}</h3>
          <button class="btn btn-ghost btn-icon" data-close-modal aria-label="Close">✕</button>
        </div>
        <div class="modal-body">${bodyHtml}</div>
        ${footerHtml ? `<div class="modal-footer">${footerHtml}</div>` : ''}
      </div>`;
    document.body.appendChild(overlay);

    const close = () => overlay.remove();
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay || e.target.closest('[data-close-modal]')) close();
    });
    document.addEventListener('keydown', function escHandler(e) {
      if (e.key === 'Escape') { close(); document.removeEventListener('keydown', escHandler); }
    });

    if (onMount) onMount(overlay, close);
    return { close, overlay };
  }

  function confirmModal({ title, message, confirmLabel = 'Confirm', danger = true, onConfirm }) {
    return openModal({
      title,
      bodyHtml: `<p style="color:var(--text-muted); font-size:13.5px; line-height:1.5;">${escapeHtml(message)}</p>`,
      footerHtml: `
        <button class="btn btn-ghost" data-close-modal>Cancel</button>
        <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" data-confirm-action>${escapeHtml(confirmLabel)}</button>
      `,
      onMount: (overlay, close) => {
        overlay.querySelector('[data-confirm-action]').addEventListener('click', async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true;
          btn.innerHTML = `<span class="spinner"></span>`;
          try {
            await onConfirm();
            close();
          } catch (err) {
            toast(err.message || 'Action failed', 'error');
            btn.disabled = false;
            btn.textContent = confirmLabel;
          }
        });
      },
    });
  }

  return {
    toast, escapeHtml, formatBytes, formatDate, timeAgo, truncHash, initials,
    badge, skeleton, emptyRow, lockedPanel, openModal, confirmModal,
  };
})();
