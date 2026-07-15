/* ==========================================================================
   CUSTODY — Auth pages (login.html / register.html)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  if (document.body.dataset.page === 'login') initLogin();
  if (document.body.dataset.page === 'register') initRegister();
});

function initLogin() {
  // Already signed in → skip straight to the console.
  if (API.isAuthenticated()) {
    location.href = 'index.html';
    return;
  }

  const form = document.getElementById('login-form');
  const banner = document.getElementById('login-error');
  const submitBtn = document.getElementById('login-submit');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    banner.classList.remove('visible');

    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    setBusy(submitBtn, true, 'Verifying…');
    try {
      const res = await API.login(username, password);
      API.setSession(res.access_token, res.refresh_token);
      location.href = 'index.html';
    } catch (err) {
      banner.textContent = err.message || 'Login failed. Check your credentials.';
      banner.classList.add('visible');
      setBusy(submitBtn, false, 'Sign in');
    }
  });

  // Demo credential quick-fill (seeded accounts from the backend startup script)
  document.querySelectorAll('[data-fill]').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.getElementById('login-username').value = btn.dataset.fill;
      document.getElementById('login-password').value = 'password123';
    });
  });
}

function initRegister() {
  if (API.isAuthenticated()) {
    location.href = 'index.html';
    return;
  }

  const form = document.getElementById('register-form');
  const banner = document.getElementById('register-error');
  const submitBtn = document.getElementById('register-submit');
  const roleGrid = document.getElementById('role-options');
  const passwordInput = document.getElementById('register-password');
  const strengthBars = document.querySelectorAll('#password-strength .bar');

  let selectedRoleId = null;

  KNOWN_ROLES.forEach((role) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'role-option';
    btn.dataset.roleId = role.id;
    btn.innerHTML = `<div class="ro-name">${role.name}</div><div class="ro-desc">${role.desc}</div>`;
    btn.addEventListener('click', () => {
      selectedRoleId = role.id;
      roleGrid.querySelectorAll('.role-option').forEach((b) => b.classList.remove('selected'));
      btn.classList.add('selected');
    });
    roleGrid.appendChild(btn);
  });
  // Default to the least-privileged role.
  roleGrid.querySelector('[data-role-id="2"]').click();

  passwordInput.addEventListener('input', () => {
    const val = passwordInput.value;
    let score = 0;
    if (val.length >= 8) score++;
    if (/[A-Z]/.test(val) && /[0-9]/.test(val)) score++;
    if (/[^A-Za-z0-9]/.test(val) && val.length >= 12) score++;
    strengthBars.forEach((bar, i) => {
      bar.className = 'bar';
      if (i < score) bar.classList.add(score === 1 ? 'on-weak' : score === 2 ? 'on-mid' : 'on-strong');
    });
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    banner.classList.remove('visible');

    const username = document.getElementById('register-username').value.trim();
    const password = passwordInput.value;
    const confirm = document.getElementById('register-confirm').value;

    if (password !== confirm) {
      banner.textContent = 'Passwords do not match.';
      banner.classList.add('visible');
      return;
    }
    if (!selectedRoleId) {
      banner.textContent = 'Select a workspace role to continue.';
      banner.classList.add('visible');
      return;
    }

    setBusy(submitBtn, true, 'Creating account…');
    try {
      await API.register(username, password, selectedRoleId);
      UI.toast('Account created — sign in to continue', 'success');
      location.href = 'login.html';
    } catch (err) {
      banner.textContent = err.message || 'Registration failed.';
      banner.classList.add('visible');
      setBusy(submitBtn, false, 'Create account');
    }
  });
}

function setBusy(btn, busy, label) {
  btn.disabled = busy;
  btn.innerHTML = busy ? `<span class="spinner"></span> ${label}` : label;
}
