// ── CONFIG ──────────────────────────────────────────────
const API = 'http://localhost:8000';

// ── TOKEN HELPERS ────────────────────────────────────────
function getToken() { return localStorage.getItem('token'); }
function setToken(t) { localStorage.setItem('token', t); }
function clearToken() { localStorage.removeItem('token'); localStorage.removeItem('student'); }

function saveStudent(s) { localStorage.setItem('student', JSON.stringify(s)); }
function getStudent() {
  try { return JSON.parse(localStorage.getItem('student')); } catch { return null; }
}

function isLoggedIn() { return !!getToken(); }

// ── REDIRECT GUARDS ──────────────────────────────────────
function requireAuth() {
  if (!isLoggedIn()) { window.location.href = 'login.html'; return false; }
  return true;
}
function redirectIfLoggedIn() {
  if (isLoggedIn()) window.location.href = 'index.html';
}

// ── API HELPERS ──────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 401) { clearToken(); window.location.href = 'login.html'; return null; }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw { status: res.status, detail: data?.detail || 'Request failed' };
  return data;
}

async function apiForm(path, formData) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    body: formData,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw { status: res.status, detail: data?.detail || 'Request failed' };
  return data;
}

// ── NAV RENDER ───────────────────────────────────────────
function renderNav(activePage) {
  const student = getStudent();
  const pages = [
    { href: 'index.html',       label: 'Dashboard'    },
    { href: 'assessments.html', label: 'Assessments'  },
    { href: 'submissions.html', label: 'Submissions'  },
    { href: 'results.html',     label: 'Results'      },
  ];

  const linksHTML = pages.map(p =>
    `<li><a href="${p.href}" class="${activePage === p.href ? 'active' : ''}">${p.label}</a></li>`
  ).join('');

  const initials = student?.name ? student.name.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase() : '?';
  const displayName = student?.name ? student.name.split(' ')[0] : 'Student';

  const navHTML = `
    <a class="nav-brand" href="index.html">Smart<span>Portal</span></a>
    <ul class="nav-links">${linksHTML}</ul>
    <div class="nav-right">
      ${isLoggedIn() ? `
        <span class="nav-user">${displayName}</span>
        <div class="dropdown">
          <div class="avatar" id="avatarBtn">${initials}</div>
          <div class="dropdown-menu" id="dropMenu">
            <a href="profile.html">My Profile</a>
            <div class="divider"></div>
            <button class="logout" onclick="logout()">Sign out</button>
          </div>
        </div>
      ` : `
        <a href="login.html" class="btn btn-primary btn-sm">Sign in</a>
      `}
    </div>
  `;

  const nav = document.querySelector('nav');
  if (nav) {
    nav.innerHTML = navHTML;
    const btn = document.getElementById('avatarBtn');
    const menu = document.getElementById('dropMenu');
    if (btn && menu) {
      btn.addEventListener('click', (e) => { e.stopPropagation(); menu.classList.toggle('show'); });
      document.addEventListener('click', () => menu.classList.remove('show'));
    }
  }
}

function logout() {
  clearToken();
  window.location.href = 'login.html';
}

// ── SCORE RING HELPER ────────────────────────────────────
function buildRing(pct) {
  const r = 28, circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const color = pct >= 75 ? 'var(--success)' : pct >= 50 ? 'var(--accent)' : 'var(--danger)';
  return `
    <svg class="ring" viewBox="0 0 68 68">
      <circle class="ring-bg" cx="34" cy="34" r="${r}"/>
      <circle class="ring-fg" cx="34" cy="34" r="${r}"
        stroke="${color}"
        stroke-dasharray="${circ}"
        stroke-dashoffset="${offset}"/>
      <text class="score-text" x="34" y="34">${Math.round(pct)}%</text>
    </svg>`;
}

// ── LOADING / EMPTY ──────────────────────────────────────
function showLoading(container) {
  container.innerHTML = `<div class="loading"><div class="spinner"></div>Loading…</div>`;
}
function showEmpty(container, icon, message) {
  container.innerHTML = `<div class="empty"><div class="empty-icon">${icon}</div><p>${message}</p></div>`;
}
function showAlert(container, type, msg) {
  container.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
}

function formatError(detail) {
  if (!detail) return 'Request failed';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(e => e.msg || JSON.stringify(e)).join('; ');
  }
  return JSON.stringify(detail);
}

// ── XSS ESCAPING (BUG 10) ───────────────────────────────
function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ── SAFE PERCENTAGE ─────────────────────────────────────
function safePct(total, max) {
  if (!max || max === 0) return 0;
  return Math.round((total / max) * 100);
}

// ── DATE FORMATTING (BUG 19) ────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}