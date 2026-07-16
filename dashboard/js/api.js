/* ==========================================================================
   CUSTODY — API client
   Thin wrapper around fetch() for the FastAPI backend mounted at /api.
   ========================================================================== */

const API = (() => {
  const BASE_URL = '/api';

  const TOKEN_KEY = 'custody_access_token';
  const REFRESH_KEY = 'custody_refresh_token';

  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function getRefreshToken() { return localStorage.getItem(REFRESH_KEY); }

  function setSession(accessToken, refreshToken) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  }

  /** Decodes the JWT payload client-side (no verification) purely for UI gating. */
  function decodeToken(token) {
    try {
      const payload = token.split('.')[1];
      const json = decodeURIComponent(
        atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
          .split('')
          .map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
          .join('')
      );
      return JSON.parse(json);
    } catch (e) {
      return null;
    }
  }

  function getSession() {
    const token = getToken();
    if (!token) return null;
    const payload = decodeToken(token);
    if (!payload) return null;
    if (payload.exp && Date.now() >= payload.exp * 1000) {
      clearSession();
      return null;
    }
    return { username: payload.sub, role: payload.role, token };
  }

  function isAuthenticated() { return !!getSession(); }

  class ApiError extends Error {
    constructor(message, status, detail) {
      super(message);
      this.status = status;
      this.detail = detail;
    }
  }

  async function request(method, path, { body, auth = true, params } = {}) {
    let url = `${BASE_URL}${path}`;
    if (params) {
      const qs = new URLSearchParams(params).toString();
      if (qs) url += `?${qs}`;
    }

    const headers = { 'Content-Type': 'application/json' };
    if (auth) {
      const token = getToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }

    let res;
    try {
      res = await fetch(url, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (networkErr) {
      throw new ApiError('Could not reach the CUSTODY gateway. Is the backend running?', 0, null);
    }

    if (res.status === 401 && auth) {
      clearSession();
      if (!location.pathname.endsWith('login.html')) {
        location.href = 'login.html';
      }
    }

    let data = null;
    const text = await res.text();
    if (text) {
      try { data = JSON.parse(text); } catch (e) { data = text; }
    }

    if (!res.ok) {
      const detail = (data && data.detail) ? data.detail : `Request failed (${res.status})`;
      throw new ApiError(detail, res.status, data);
    }

    return data;
  }

  return {
    // --- session ---
    getSession, isAuthenticated, setSession, clearSession, getToken, getRefreshToken, ApiError,

    // --- auth ---
    login: (username, password) => request('POST', '/auth/login', { body: { username, password }, auth: false }),
    register: (username, password, role_id) => request('POST', '/auth/register', { body: { username, password, role_id }, auth: false }),
    //logout: (token) => request('POST', '/auth/logout', { params: { token } }),
    logout: (token) =>
      request('POST', '/auth/logout', {
        body: { token }
      }),
    // --- dashboard ---
    getDashboardSummary: () => request('GET', '/dashboard/summary'),

    // --- health ---
    getInfraHealth: () => request('GET', '/health/vms'),

    // --- backups ---
    listBackups: () => request('GET', '/backups'),
    getBackupVersions: (fileId) => request('GET', `/backups/${fileId}/versions`),
    purgeBackupVersion: (versionId) => request('DELETE', `/backups/versions/${versionId}`),

    // --- restore ---
    listRestoreRequests: () => request('GET', '/restore/requests'),
    createRestoreRequest: (backup_version_id, destination_path) =>
      request('POST', '/restore/requests', { body: { backup_version_id, destination_path } }),
    approveRestore: (requestId) => request('POST', `/restore/requests/${requestId}/approve`),
    rejectRestore: (requestId, reason) => request('POST', `/restore/requests/${requestId}/reject`, { body: { reason } }),

    // --- quarantine ---
    listQuarantine: () => request('GET', '/quarantine'),
    releaseQuarantine: (fileId, release_to_path) =>
      request('POST', `/quarantine/${fileId}/release`, { body: { release_to_path } }),
    purgeQuarantine: (fileId) => request('DELETE', `/quarantine/${fileId}/purge`),

    // --- users ---
    listUsers: () => request('GET', '/users'),
    createUser: (payload) => request('POST', '/users', { body: payload }),
    updateUser: (userId, payload) => request('PATCH', `/users/${userId}`, { body: payload }),
    lockUser: (userId) => request('POST', `/users/${userId}/lock`),
    unlockUser: (userId) => request('POST', `/users/${userId}/unlock`),
    resetPassword: (userId, new_password) => request('POST', `/users/${userId}/reset-password`, { body: { new_password } }),

    // --- settings ---
    getSettings: () => request('GET', '/settings'),
    updateSettings: (payload) => request('PUT', '/settings', { body: payload }),

    // --- logs ---
    getAuditLog: () => request('GET', '/logs/audit'),
  };
})();

/**
 * Role → permission matrix mirrored from the backend seed data in app.py.
 * Used purely for client-side UI gating; the API is the real enforcement point.
 */
const ROLE_PERMISSIONS = {
  Admin: [
    'backups.view', 'backups.delete',
    'restore.view', 'restore.request', 'restore.approve',
    'quarantine.view', 'quarantine.manage',
    'users.view', 'users.create', 'users.edit', 'users.lock',
    'settings.view', 'settings.edit',
    'logs.view',
  ],
  Operator: ['backups.view', 'restore.view', 'restore.request', 'quarantine.view', 'logs.view'],
  Auditor: ['backups.view', 'restore.view', 'quarantine.view', 'logs.view', 'settings.view'],
};

/** Known seed roles. There is no GET /roles endpoint on the backend, so the
 *  register page mirrors the fixed Admin(1) / Operator(2) / Auditor(3) seed order. */
const KNOWN_ROLES = [
  { id: 1, name: 'Admin', desc: 'Full system control, user management, settings' },
  { id: 2, name: 'Operator', desc: 'Runs backups, requests restores, views quarantine' },
  { id: 3, name: 'Auditor', desc: 'Read-only visibility across logs and compliance data' },
];

function can(role, permission) {
  return (ROLE_PERMISSIONS[role] || []).includes(permission);
}
