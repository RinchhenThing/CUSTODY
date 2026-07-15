/* ==========================================================================
   CUSTODY — Feature modules
   One render(viewEl, opts) function per nav section. Each owns its markup,
   data fetch, and event wiring.
   ========================================================================== */

/* -------------------------------------------------------------------- */
/* Overview                                                              */
/* -------------------------------------------------------------------- */
async function renderOverview(view, opts) {
  if (!view.dataset.mounted) {
    view.innerHTML = `
      <div class="view-head">
        <div><h2>System Overview</h2><p>Live posture across backups, quarantine, and infrastructure.</p></div>
      </div>
      <div class="stat-grid" id="ov-stats">
        ${Array.from({ length: 4 }).map(() => `<div class="stat-card"><div class="eyebrow">Loading</div><div class="stat-value">—</div></div>`).join('')}
      </div>
      <div class="two-col">
        <div class="panel">
          <div class="panel-header"><h2>Hypervisor Health</h2><a href="#health" class="btn btn-ghost btn-sm">View all →</a></div>
          <div class="panel-body"><div class="health-grid" id="ov-health"><div class="loading-line"><span class="spinner"></span> Pinging agents…</div></div></div>
        </div>
        <div class="panel">
          <div class="panel-header"><h2>Recent Restore Activity</h2><a href="#restore" class="btn btn-ghost btn-sm">Open queue →</a></div>
          <div class="panel-body panel-body--flush" id="ov-restore"><div class="loading-line"><span class="spinner"></span> Loading…</div></div>
        </div>
      </div>`;
    view.dataset.mounted = '1';
  }

  const canRestore = can(session.role, 'restore.view');

  const [summary, health] = await Promise.all([
    API.getDashboardSummary(),
    API.getInfraHealth(),
  ]);

  const statCards = [
    { label: 'Total Backups', value: summary.total_backups, tone: '' },
    { label: 'Quarantined Objects', value: summary.active_quarantine_count, tone: summary.active_quarantine_count > 0 ? 'warn' : 'up' },
    { label: 'Unread Alerts', value: summary.critical_alerts, tone: summary.critical_alerts > 0 ? 'critical' : 'up' },
    { label: 'System Status', value: summary.system_status, tone: summary.system_status === 'SECURE' ? 'up' : 'critical', isText: true },
  ];
  document.getElementById('ov-stats').innerHTML = statCards.map((s) => `
    <div class="stat-card">
      <div class="eyebrow">${s.label}</div>
      <div class="stat-value ${s.tone}" style="${s.isText ? 'font-size:20px;' : ''}">${s.value}</div>
      <div class="stat-foot">as of ${new Date().toLocaleTimeString()}</div>
    </div>`).join('');

  document.getElementById('ov-health').innerHTML = Object.entries(health)
    .filter(([k]) => k !== 'timestamp')
    .map(([name, node]) => healthNodeHtml(name, node)).join('');

  const restoreBox = document.getElementById('ov-restore');
  if (!canRestore) {
    restoreBox.innerHTML = UI.lockedPanel('Restore visibility requires the restore.view capability.');
  } else {
    const requests = await API.listRestoreRequests();
    const recent = [...requests].sort((a, b) => new Date(b.requested_at) - new Date(a.requested_at)).slice(0, 5);
    restoreBox.innerHTML = recent.length ? `
      <div class="chain" style="padding:20px 20px 20px 32px;">
        ${recent.map((r) => `
          <div class="chain-node ${r.status === 'REJECTED' || r.status === 'FAILED' ? 'node-critical' : r.status === 'PENDING' ? 'node-warn' : ''}">
            <div style="display:flex; justify-content:space-between; gap:10px;">
              <span style="font-size:13px;">Version <span class="hash">#${r.backup_version_id}</span> → ${UI.escapeHtml(r.destination_path)}</span>
              ${UI.badge(r.status)}
            </div>
            <div class="eyebrow" style="margin-top:4px;">${UI.timeAgo(r.requested_at)}</div>
          </div>`).join('')}
      </div>` : `<div class="empty-state"><p>No restore requests yet.</p></div>`;
  }
}

function healthNodeHtml(name, node) {
  const status = node.status || 'OFFLINE';
  return `
    <div class="health-node">
      <div class="hn-name"><span>${name.replace(/_/g, ' ')}</span></div>
      ${UI.badge(status)}
      ${node.error ? `<div class="field-hint" style="margin-top:8px;">${UI.escapeHtml(node.error)}</div>` : ''}
    </div>`;
}

/* -------------------------------------------------------------------- */
/* Backups                                                               */
/* -------------------------------------------------------------------- */
async function renderBackups(view) {
  const canDelete = can(session.role, 'backups.delete');

  if (!view.dataset.mounted) {
    view.innerHTML = `
      <div class="view-head">
        <div><h2>Backup Vault</h2><p>Every tracked production path and its cryptographically hashed version history.</p></div>
      </div>
      <div class="panel">
        <div class="panel-body panel-body--flush table-wrap">
          <table class="data-table">
            <thead><tr><th>File</th><th>Original Path</th><th>Versions</th><th>Latest Hash</th><th>Tracked Since</th><th></th></tr></thead>
            <tbody id="backups-tbody">${UI.skeleton(6)}</tbody>
          </table>
        </div>
      </div>`;
    view.dataset.mounted = '1';
  }

  const files = await API.listBackups();
  const tbody = document.getElementById('backups-tbody');

  if (!files.length) {
    tbody.innerHTML = UI.emptyRow(6, 'No backup files tracked yet.');
    return;
  }

  tbody.innerHTML = files.map((f) => {
    const latest = [...f.versions].sort((a, b) => b.version_number - a.version_number)[0];
    return `
      <tr>
        <td>${UI.escapeHtml(f.filename)}</td>
        <td class="cell-muted mono" style="font-size:12px;">${UI.escapeHtml(f.original_path)}</td>
        <td>${f.versions.length}</td>
        <td>${latest ? `<span class="hash">${UI.truncHash(latest.sha256_hash)}</span>` : '—'}</td>
        <td class="cell-muted">${UI.formatDate(f.created_at)}</td>
        <td class="cell-actions">
          <button class="btn btn-ghost btn-sm" data-expand-file="${f.id}">Versions</button>
        </td>
      </tr>
      <tr class="versions-row" id="versions-row-${f.id}" style="display:none;">
        <td colspan="6" style="background:var(--void); padding:0;">
          <div id="versions-body-${f.id}" style="padding:14px 20px;"></div>
        </td>
      </tr>`;
  }).join('');

  tbody.querySelectorAll('[data-expand-file]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const fileId = btn.dataset.expandFile;
      const row = document.getElementById(`versions-row-${fileId}`);
      const body = document.getElementById(`versions-body-${fileId}`);
      const opening = row.style.display === 'none';
      row.style.display = opening ? 'table-row' : 'none';
      btn.textContent = opening ? 'Hide' : 'Versions';
      if (opening && !body.dataset.loaded) {
        body.innerHTML = `<div class="loading-line"><span class="spinner"></span> Fetching version chain…</div>`;
        const versions = await API.getBackupVersions(fileId);
        body.dataset.loaded = '1';
        body.innerHTML = `
          <div class="chain">
            ${versions.sort((a, b) => b.version_number - a.version_number).map((v) => `
              <div class="chain-node">
                <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;">
                  <div>
                    <strong>v${v.version_number}</strong>
                    <span class="hash" style="margin-left:8px;">${v.sha256_hash}</span>
                  </div>
                  <div style="display:flex; align-items:center; gap:10px;">
                    <span class="cell-muted">${UI.formatBytes(v.file_size)}</span>
                    <span class="eyebrow">${UI.formatDate(v.created_at)}</span>
                    ${canDelete ? `<button class="btn btn-danger btn-sm" data-purge-version="${v.id}">Purge</button>` : ''}
                  </div>
                </div>
              </div>`).join('')}
          </div>`;
        if (canDelete) {
          body.querySelectorAll('[data-purge-version]').forEach((pbtn) => {
            pbtn.addEventListener('click', () => {
              UI.confirmModal({
                title: 'Purge backup version',
                message: 'This permanently deletes this version from the database and instructs the Backup VM agent to erase the underlying binary. This cannot be undone.',
                confirmLabel: 'Purge permanently',
                onConfirm: async () => {
                  await API.purgeBackupVersion(pbtn.dataset.purgeVersion);
                  UI.toast('Backup version purged', 'success');
                  body.dataset.loaded = '';
                  btn.click(); btn.click();
                },
              });
            });
          });
        }
      }
    });
  });
}

/* -------------------------------------------------------------------- */
/* Restore queue                                                         */
/* -------------------------------------------------------------------- */
async function renderRestore(view) {
  const canApprove = can(session.role, 'restore.approve');
  const canRequest = can(session.role, 'restore.request');

  if (!view.dataset.mounted) {
    view.innerHTML = `
      <div class="view-head">
        <div><h2>Restore Authorization Queue</h2><p>Recovery requests awaiting review, or already processed.</p></div>
        ${canRequest ? `<button class="btn btn-primary" id="btn-new-restore">+ New restore request</button>` : ''}
      </div>
      <div class="panel">
        <div class="panel-body panel-body--flush table-wrap">
          <table class="data-table">
            <thead><tr><th>Request</th><th>Destination</th><th>Requested</th><th>Status</th><th></th></tr></thead>
            <tbody id="restore-tbody">${UI.skeleton(5)}</tbody>
          </table>
        </div>
      </div>`;
    view.dataset.mounted = '1';

    if (canRequest) {
      document.getElementById('btn-new-restore').addEventListener('click', openNewRestoreModal);
    }
  }

  const requests = await API.listRestoreRequests();
  const tbody = document.getElementById('restore-tbody');

  if (!requests.length) {
    tbody.innerHTML = UI.emptyRow(5, 'No restore requests in the queue.');
    return;
  }

  const sorted = [...requests].sort((a, b) => new Date(b.requested_at) - new Date(a.requested_at));
  tbody.innerHTML = sorted.map((r) => `
    <tr>
      <td>Version <span class="hash">#${r.backup_version_id}</span></td>
      <td class="cell-muted mono" style="font-size:12px;">${UI.escapeHtml(r.destination_path)}</td>
      <td class="cell-muted">${UI.timeAgo(r.requested_at)}</td>
      <td>${UI.badge(r.status)}</td>
      <td class="cell-actions">
        ${canApprove && r.status === 'PENDING' ? `
          <button class="btn btn-verify btn-sm" data-approve="${r.id}">Approve</button>
          <button class="btn btn-danger btn-sm" data-reject="${r.id}">Reject</button>
        ` : r.rejection_reason ? `<span class="field-hint">${UI.escapeHtml(r.rejection_reason)}</span>` : ''}
      </td>
    </tr>`).join('');

  tbody.querySelectorAll('[data-approve]').forEach((btn) => {
    btn.addEventListener('click', () => {
      UI.confirmModal({
        title: 'Approve restore request',
        message: 'This triggers integrity verification and transport of the backup back to production. Continue?',
        confirmLabel: 'Approve & execute',
        danger: false,
        onConfirm: async () => {
          await API.approveRestore(btn.dataset.approve);
          UI.toast('Restore approved and executed', 'success');
          view.dataset.mounted = '';
          renderRestore(view);
        },
      });
    });
  });

  tbody.querySelectorAll('[data-reject]').forEach((btn) => {
    btn.addEventListener('click', () => {
      UI.openModal({
        title: 'Reject restore request',
        bodyHtml: `
          <div class="field">
            <label for="reject-reason">Reason</label>
            <textarea id="reject-reason" rows="3" placeholder="Explain why this request is denied…"></textarea>
          </div>`,
        footerHtml: `
          <button class="btn btn-ghost" data-close-modal>Cancel</button>
          <button class="btn btn-danger" id="confirm-reject">Reject request</button>`,
        onMount: (overlay, close) => {
          overlay.querySelector('#confirm-reject').addEventListener('click', async () => {
            const reason = overlay.querySelector('#reject-reason').value.trim();
            if (!reason) { UI.toast('A rejection reason is required', 'error'); return; }
            await API.rejectRestore(btn.dataset.reject, reason);
            UI.toast('Restore request rejected', 'success');
            close();
            view.dataset.mounted = '';
            renderRestore(view);
          });
        },
      });
    });
  });
}

async function openNewRestoreModal() {
  const files = await API.listBackups();
  const versionOptions = files.flatMap((f) =>
    f.versions.map((v) => `<option value="${v.id}">${f.filename} — v${v.version_number} (${UI.truncHash(v.sha256_hash, 8)})</option>`)
  );

  UI.openModal({
    title: 'New restore request',
    bodyHtml: `
      <div class="field">
        <label for="rr-version">Backup version</label>
        <select id="rr-version">${versionOptions.length ? versionOptions.join('') : '<option disabled>No versions available</option>'}</select>
      </div>
      <div class="field">
        <label for="rr-dest">Destination path</label>
        <input id="rr-dest" type="text" placeholder="/production/restore/target" />
      </div>`,
    footerHtml: `
      <button class="btn btn-ghost" data-close-modal>Cancel</button>
      <button class="btn btn-primary" id="confirm-new-restore">Submit request</button>`,
    onMount: (overlay, close) => {
      overlay.querySelector('#confirm-new-restore').addEventListener('click', async () => {
        const versionId = overlay.querySelector('#rr-version').value;
        const dest = overlay.querySelector('#rr-dest').value.trim();
        if (!versionId || !dest) { UI.toast('Select a version and destination path', 'error'); return; }
        await API.createRestoreRequest(Number(versionId), dest);
        UI.toast('Restore request submitted for approval', 'success');
        close();
        const view = document.getElementById('view-restore');
        view.dataset.mounted = '';
        renderRestore(view);
      });
    },
  });
}

/* -------------------------------------------------------------------- */
/* Quarantine                                                            */
/* -------------------------------------------------------------------- */
async function renderQuarantine(view) {
  const canManage = can(session.role, 'quarantine.manage');

  if (!view.dataset.mounted) {
    view.innerHTML = `
      <div class="view-head">
        <div><h2>Quarantine Sandbox</h2><p>Suspicious or confirmed-malicious payloads isolated from production.</p></div>
      </div>
      <div class="panel">
        <div class="panel-body panel-body--flush table-wrap">
          <table class="data-table">
            <thead><tr><th>Filename</th><th>SHA-256</th><th>Size</th><th>Reason</th><th>Status</th><th>Captured</th><th></th></tr></thead>
            <tbody id="quarantine-tbody">${UI.skeleton(7)}</tbody>
          </table>
        </div>
      </div>`;
    view.dataset.mounted = '1';
  }

  const files = await API.listQuarantine();
  const tbody = document.getElementById('quarantine-tbody');

  if (!files.length) {
    tbody.innerHTML = UI.emptyRow(7, 'Sandbox is empty — nothing isolated.');
    return;
  }

  tbody.innerHTML = files.map((f) => `
    <tr>
      <td>${UI.escapeHtml(f.filename)}</td>
      <td><span class="hash">${UI.truncHash(f.sha256_hash)}</span></td>
      <td class="cell-muted">${UI.formatBytes(f.size)}</td>
      <td class="cell-muted" style="max-width:220px; white-space:normal;">${UI.escapeHtml(f.detected_reason)}</td>
      <td>${UI.badge(f.status)}</td>
      <td class="cell-muted">${UI.timeAgo(f.captured_at)}</td>
      <td class="cell-actions">
        ${canManage && f.status === 'ISOLATED' ? `
          <button class="btn btn-verify btn-sm" data-release="${f.id}">Release</button>
          <button class="btn btn-danger btn-sm" data-purge="${f.id}">Purge</button>` : ''}
      </td>
    </tr>`).join('');

  tbody.querySelectorAll('[data-release]').forEach((btn) => {
    btn.addEventListener('click', () => {
      UI.openModal({
        title: 'Release from quarantine',
        bodyHtml: `
          <div class="field">
            <label for="release-path">Release destination path</label>
            <input id="release-path" type="text" placeholder="/production/restore/target" />
          </div>`,
        footerHtml: `
          <button class="btn btn-ghost" data-close-modal>Cancel</button>
          <button class="btn btn-verify" id="confirm-release">Release file</button>`,
        onMount: (overlay, close) => {
          overlay.querySelector('#confirm-release').addEventListener('click', async () => {
            const path = overlay.querySelector('#release-path').value.trim();
            if (!path) { UI.toast('Destination path is required', 'error'); return; }
            await API.releaseQuarantine(btn.dataset.release, path);
            UI.toast('File released from quarantine', 'success');
            close();
            view.dataset.mounted = '';
            renderQuarantine(view);
          });
        },
      });
    });
  });

  tbody.querySelectorAll('[data-purge]').forEach((btn) => {
    btn.addEventListener('click', () => {
      UI.confirmModal({
        title: 'Permanently purge payload',
        message: 'This eliminates the confirmed malicious binary from isolated storage. This cannot be undone.',
        confirmLabel: 'Purge permanently',
        onConfirm: async () => {
          await API.purgeQuarantine(btn.dataset.purge);
          UI.toast('Payload purged', 'success');
          view.dataset.mounted = '';
          renderQuarantine(view);
        },
      });
    });
  });
}

/* -------------------------------------------------------------------- */
/* Infrastructure health                                                 */
/* -------------------------------------------------------------------- */
async function renderHealth(view) {
  if (!view.dataset.mounted) {
    view.innerHTML = `
      <div class="view-head"><div><h2>Hypervisor Node Health</h2><p>Live reachability of the four VM agents behind the gateway.</p></div></div>
      <div class="health-grid" id="health-grid" style="grid-template-columns:repeat(2,1fr);">${UI.skeleton(1)}</div>`;
    view.dataset.mounted = '1';
  }

  const health = await API.getInfraHealth();
  const grid = document.getElementById('health-grid');
  const entries = Object.entries(health).filter(([k]) => k !== 'timestamp');

  grid.innerHTML = entries.map(([name, node]) => `
    <div class="panel">
      <div class="panel-body">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <strong>${name.replace(/_/g, ' ')}</strong>
          ${UI.badge(node.status)}
        </div>
        ${node.error
          ? `<div class="field-hint">${UI.escapeHtml(node.error)}</div>`
          : `<div class="field-hint mono">${node.data ? UI.escapeHtml(JSON.stringify(node.data)) : 'No payload'}</div>`}
      </div>
    </div>`).join('');

  const stamp = document.getElementById('health-stamp');
  if (!stamp) {
    const p = document.createElement('p');
    p.id = 'health-stamp';
    p.className = 'eyebrow';
    p.style.marginTop = '14px';
    view.appendChild(p);
  }
  document.getElementById('health-stamp').textContent = `Last polled ${new Date(health.timestamp).toLocaleTimeString()}`;
}

/* -------------------------------------------------------------------- */
/* Users                                                                 */
/* -------------------------------------------------------------------- */
async function renderUsers(view) {
  const canCreate = can(session.role, 'users.create');
  const canEdit = can(session.role, 'users.edit');
  const canLock = can(session.role, 'users.lock');

  if (!view.dataset.mounted) {
    view.innerHTML = `
      <div class="view-head">
        <div><h2>User Access</h2><p>Console operator accounts and their assigned workspace roles.</p></div>
        ${canCreate ? `<button class="btn btn-primary" id="btn-new-user">+ New user</button>` : ''}
      </div>
      <div class="panel">
        <div class="panel-body panel-body--flush table-wrap">
          <table class="data-table">
            <thead><tr><th>Username</th><th>Role</th><th>Status</th><th>Created</th><th></th></tr></thead>
            <tbody id="users-tbody">${UI.skeleton(5)}</tbody>
          </table>
        </div>
      </div>`;
    view.dataset.mounted = '1';
    if (canCreate) document.getElementById('btn-new-user').addEventListener('click', () => openUserModal());
  }

  const users = await API.listUsers();
  const tbody = document.getElementById('users-tbody');

  tbody.innerHTML = users.map((u) => `
    <tr>
      <td><strong>${UI.escapeHtml(u.username)}</strong></td>
      <td>${u.role ? UI.escapeHtml(u.role.name) : `role #${u.role_id}`}</td>
      <td>${u.is_locked ? UI.badge('LOCKED') : (u.is_active ? UI.badge('ONLINE', 'Active') : UI.badge('OFFLINE', 'Inactive'))}</td>
      <td class="cell-muted">${UI.formatDate(u.created_at)}</td>
      <td class="cell-actions">
        ${canLock ? (u.is_locked
          ? `<button class="btn btn-verify btn-sm" data-unlock="${u.id}">Unlock</button>`
          : `<button class="btn btn-danger btn-sm" data-lock="${u.id}">Lock</button>`) : ''}
        ${canEdit ? `<button class="btn btn-ghost btn-sm" data-reset="${u.id}" data-username="${UI.escapeHtml(u.username)}">Reset password</button>` : ''}
      </td>
    </tr>`).join('') || UI.emptyRow(5, 'No users found.');

  tbody.querySelectorAll('[data-lock]').forEach((btn) => btn.addEventListener('click', async () => {
    await API.lockUser(btn.dataset.lock); UI.toast('User locked', 'success'); view.dataset.mounted = ''; renderUsers(view);
  }));
  tbody.querySelectorAll('[data-unlock]').forEach((btn) => btn.addEventListener('click', async () => {
    await API.unlockUser(btn.dataset.unlock); UI.toast('User unlocked', 'success'); view.dataset.mounted = ''; renderUsers(view);
  }));
  tbody.querySelectorAll('[data-reset]').forEach((btn) => btn.addEventListener('click', () => {
    UI.openModal({
      title: `Reset password — ${btn.dataset.username}`,
      bodyHtml: `<div class="field"><label for="new-pass">New password</label><input id="new-pass" type="password" placeholder="Minimum 8 characters" /></div>`,
      footerHtml: `<button class="btn btn-ghost" data-close-modal>Cancel</button><button class="btn btn-primary" id="confirm-reset">Reset password</button>`,
      onMount: (overlay, close) => {
        overlay.querySelector('#confirm-reset').addEventListener('click', async () => {
          const val = overlay.querySelector('#new-pass').value;
          if (val.length < 8) { UI.toast('Password must be at least 8 characters', 'error'); return; }
          await API.resetPassword(btn.dataset.reset, val);
          UI.toast('Password reset', 'success');
          close();
        });
      },
    });
  }));
}

function openUserModal() {
  const roleOptions = KNOWN_ROLES.map((r) => `<option value="${r.id}">${r.name}</option>`).join('');
  UI.openModal({
    title: 'Create console user',
    bodyHtml: `
      <div class="field"><label for="nu-username">Username</label><input id="nu-username" type="text" /></div>
      <div class="field"><label for="nu-password">Password</label><input id="nu-password" type="password" /></div>
      <div class="field"><label for="nu-role">Role</label><select id="nu-role">${roleOptions}</select></div>`,
    footerHtml: `<button class="btn btn-ghost" data-close-modal>Cancel</button><button class="btn btn-primary" id="confirm-new-user">Create user</button>`,
    onMount: (overlay, close) => {
      overlay.querySelector('#confirm-new-user').addEventListener('click', async () => {
        const username = overlay.querySelector('#nu-username').value.trim();
        const password = overlay.querySelector('#nu-password').value;
        const role_id = Number(overlay.querySelector('#nu-role').value);
        if (!username || password.length < 8) { UI.toast('Username and an 8+ character password are required', 'error'); return; }
        await API.createUser({ username, password, role_id, is_active: true, is_locked: false });
        UI.toast('User created', 'success');
        close();
        const view = document.getElementById('view-users');
        view.dataset.mounted = '';
        renderUsers(view);
      });
    },
  });
}

/* -------------------------------------------------------------------- */
/* Audit log                                                             */
/* -------------------------------------------------------------------- */
async function renderLogs(view) {
  if (!view.dataset.mounted) {
    view.innerHTML = `
      <div class="view-head"><div><h2>Audit Log</h2><p>Immutable record of every authenticated request made to the gateway.</p></div></div>
      <div class="panel">
        <div class="panel-body panel-body--flush table-wrap">
          <table class="data-table">
            <thead><tr><th>Time</th><th>User</th><th>Role</th><th>Action</th><th>Target</th><th>IP</th><th>Status</th></tr></thead>
            <tbody id="logs-tbody">${UI.skeleton(7)}</tbody>
          </table>
        </div>
      </div>`;
    view.dataset.mounted = '1';
  }

  const logs = await API.getAuditLog();
  const tbody = document.getElementById('logs-tbody');

  if (!logs.length) {
    tbody.innerHTML = UI.emptyRow(7, 'No audit entries recorded yet.');
    return;
  }

  tbody.innerHTML = logs.slice(0, 200).map((l) => `
    <tr>
      <td class="cell-muted" style="white-space:nowrap;">${UI.formatDate(l.timestamp)}</td>
      <td>${UI.escapeHtml(l.user)}</td>
      <td class="cell-muted">${UI.escapeHtml(l.role)}</td>
      <td><span class="hash">${UI.escapeHtml(l.action)}</span></td>
      <td class="cell-muted mono" style="font-size:12px;">${UI.escapeHtml(l.target)}</td>
      <td class="cell-muted">${UI.escapeHtml(l.ip_address)}</td>
      <td>${l.status.startsWith('SUCCESS') ? UI.badge('SUCCESS') : UI.badge('FAILED', l.status)}</td>
    </tr>`).join('');
}

/* -------------------------------------------------------------------- */
/* Settings                                                              */
/* -------------------------------------------------------------------- */
async function renderSettings(view) {
  const canEdit = can(session.role, 'settings.edit');

  if (!view.dataset.mounted) {
    view.innerHTML = `
      <div class="view-head"><div><h2>System Settings</h2><p>Global thresholds enforced by the detection and retention engines.</p></div></div>
      <div class="panel"><div class="panel-body" id="settings-body"><div class="loading-line"><span class="spinner"></span> Loading configuration…</div></div></div>`;
    view.dataset.mounted = '1';
  }

  const settings = await API.getSettings();
  const body = document.getElementById('settings-body');
  const entries = Object.entries(settings);

  const labels = {
    SCAN_DELAY_SECONDS: 'Scan delay (seconds)',
    MAX_VERSION_COUNT: 'Max retained versions per file',
    ALERT_ON_SUSPICIOUS: 'Alert on suspicious activity',
    QUARANTINE_RETENTION_DAYS: 'Quarantine retention (days)',
  };

  body.innerHTML = `
    <form id="settings-form">
      ${entries.map(([key, val]) => `
        <div class="field">
          <label for="set-${key}">${labels[key] || key}</label>
          <input id="set-${key}" data-setting-key="${key}" type="text" value="${UI.escapeHtml(val)}" ${canEdit ? '' : 'disabled'} />
        </div>`).join('')}
      ${canEdit ? `<button type="submit" class="btn btn-primary">Save configuration</button>` : `<p class="field-hint">Read-only for your role.</p>`}
    </form>`;

  if (canEdit) {
    document.getElementById('settings-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {};
      body.querySelectorAll('[data-setting-key]').forEach((input) => { payload[input.dataset.settingKey] = input.value; });
      const btn = e.target.querySelector('button[type="submit"]');
      setBusy(btn, true, 'Saving…');
      try {
        await API.updateSettings(payload);
        UI.toast('Configuration updated', 'success');
      } catch (err) {
        UI.toast(err.message || 'Failed to save settings', 'error');
      } finally {
        setBusy(btn, false, 'Save configuration');
      }
    });
  }
}
