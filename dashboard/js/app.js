/* ==========================================================================
   CUSTODY — Dashboard shell (index.html)
   Lightweight hash-router over a single-page console shell.
   ========================================================================== */

const ICONS = {
  overview: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>',
  backups: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5"/><path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3"/></svg>',
  restore: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>',
  quarantine: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2l8 4v6c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-4z"/><path d="M9.5 12l2 2 3.5-3.5"/></svg>',
  health: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12h4l2-7 4 14 2-7h6"/></svg>',
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="9" cy="8" r="3.2"/><path d="M2.5 20c0-3.6 3-6 6.5-6s6.5 2.4 6.5 6"/><circle cx="17.5" cy="8.5" r="2.4"/><path d="M15.8 14.3c2.6.5 4.7 2.5 4.7 5.7"/></svg>',
  logs: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M14 2v5h5"/><path d="M8 13h8M8 17h5"/></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 13.5a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V20a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 9 18.36a1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.55-1H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.64 9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.55V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87V9c.14.6.62 1.09 1.55 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.51 1.5z"/></svg>',
};

const NAV = [
  { id: 'overview',   label: 'Overview',        icon: 'overview',   perm: null,             render: 'renderOverview' },
  { id: 'backups',    label: 'Backups',         icon: 'backups',    perm: 'backups.view',   render: 'renderBackups' },
  { id: 'restore',    label: 'Restore Queue',   icon: 'restore',    perm: 'restore.view',   render: 'renderRestore' },
  { id: 'quarantine', label: 'Quarantine',      icon: 'quarantine', perm: 'quarantine.view',render: 'renderQuarantine' },
  { id: 'health',     label: 'Infra Health',    icon: 'health',     perm: null,             render: 'renderHealth' },
  { id: 'users',      label: 'User Access',     icon: 'users',      perm: 'users.view',     render: 'renderUsers' },
  { id: 'logs',       label: 'Audit Log',       icon: 'logs',       perm: 'logs.view',      render: 'renderLogs' },
  { id: 'settings',   label: 'System Settings', icon: 'settings',   perm: 'settings.view',  render: 'renderSettings' },
];

let session = null;

document.addEventListener('DOMContentLoaded', () => {
  session = API.getSession();
  if (!session) {
    location.href = 'login.html';
    return;
  }

  buildSidebar();
  buildUserChip();
  wireLogout();

  window.addEventListener('hashchange', route);
  route();

  // Light auto-refresh for the active view — keeps status data current.
  setInterval(() => route({ silent: true }), 30000);
});

function buildSidebar() {
  const primary = document.getElementById('nav-primary');
  primary.innerHTML = NAV.map((item) => {
    const locked = item.perm && !can(session.role, item.perm);
    if (locked) return '';
    return `
      <a href="#${item.id}" class="nav-link" data-nav="${item.id}">
        ${ICONS[item.icon]}
        <span>${item.label}</span>
      </a>`;
  }).join('');
}

function buildUserChip() {
  document.getElementById('chip-initials').textContent = UI.initials(session.username);
  document.getElementById('chip-username').textContent = session.username;
  document.getElementById('chip-role').textContent = session.role;
}

function wireLogout() {
  document.getElementById('btn-logout').addEventListener('click', async () => {
    try { await API.logout(API.getToken()); } catch (e) { /* best-effort */ }
    API.clearSession();
    location.href = 'login.html';
  });
}

function currentRoute() {
  const hash = location.hash.replace('#', '');
  return NAV.find((n) => n.id === hash) ? hash : 'overview';
}

async function route(opts = {}) {
  const routeId = currentRoute();
  const item = NAV.find((n) => n.id === routeId);

  document.querySelectorAll('.nav-link').forEach((a) => a.classList.toggle('active', a.dataset.nav === routeId));

  const titleEl = document.getElementById('topbar-view-title');
  const eyebrowEl = document.getElementById('topbar-view-eyebrow');
  titleEl.textContent = item.label;
  eyebrowEl.textContent = describeRoute(routeId);

  const content = document.getElementById('content');
  let view = document.getElementById(`view-${routeId}`);
  if (!view) {
    view = document.createElement('div');
    view.id = `view-${routeId}`;
    view.className = 'view';
    content.appendChild(view);
  }
  document.querySelectorAll('.view').forEach((v) => v.classList.toggle('active', v.id === `view-${routeId}`));

  if (item.perm && !can(session.role, item.perm)) {
    view.innerHTML = UI.lockedPanel(`Your role (${session.role}) does not have the "${item.perm}" capability.`);
    return;
  }

  const renderFn = window[item.render];
  if (typeof renderFn === 'function') {
    try {
      await renderFn(view, { silent: !!opts.silent });
    } catch (err) {
      if (!opts.silent) UI.toast(err.message || 'Failed to load section', 'error');
      if (!view.innerHTML) {
        view.innerHTML = `<div class="empty-state"><p>Could not load this section. ${UI.escapeHtml(err.message || '')}</p></div>`;
      }
    }
  }
}

function describeRoute(id) {
  const map = {
    overview: 'Console / Overview',
    backups: 'Console / Backup Vault',
    restore: 'Console / Restore Authorization',
    quarantine: 'Console / Sandbox',
    health: 'Console / Hypervisor Nodes',
    users: 'Console / Access Control',
    logs: 'Console / Compliance',
    settings: 'Console / Global Configuration',
  };
  return map[id] || 'Console';
}
