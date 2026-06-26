// ── CONFIG ──────────────────────────────────────────────
const API = 'http://localhost:8000';


// ── TOKEN HELPERS ────────────────────────────────────────
function getToken()  { return localStorage.getItem('token'); }
function setToken(t) { localStorage.setItem('token', t); }
function clearToken(){ localStorage.removeItem('token'); localStorage.removeItem('student'); }

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
  const res = await fetch(`${API}${path}`, { method: 'POST', body: formData });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw { status: res.status, detail: data?.detail || 'Request failed' };
  return data;
}




function renderNav(activePage) {
  const student = getStudent();
  const pages = [
    { href: 'index.html',       label: 'Dashboard'   },
    { href: 'assessments.html', label: 'Assessments' },
    { href: 'practice.html',    label: '✦ AI Practice', ai: true },
    { href: 'submissions.html', label: 'Submissions'  },
    { href: 'results.html',     label: 'Results'      },
  ];

  const linksHTML = pages.map(p =>
    `<li><a href="${p.href}" class="${activePage === p.href ? 'active' : ''}">${escapeHtml(p.label)}</a></li>`
  ).join('');

  const initials    = student?.name ? student.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() : '?';
  const displayName = student?.name ? student.name.split(' ')[0] : 'Student';

  const navHTML = `
    <a class="nav-brand" href="index.html">Smart<span>Portal</span></a>
    <ul class="nav-links">${linksHTML}</ul>
    <div class="nav-right">
      ${isLoggedIn() ? `
        <span class="nav-user">${escapeHtml(displayName)}</span>
        <div class="dropdown">
          <div class="avatar" id="avatarBtn">${escapeHtml(initials)}</div>
          <div class="dropdown-menu" id="dropMenu">
            <a href="profile.html">My Profile</a>
            <div class="divider"></div>
            <button class="logout" onclick="logout()">Sign out</button>
          </div>
        </div>
      ` : `<a href="login.html" class="btn btn-primary btn-sm">Sign in</a>`}
      <button class="hamburger" id="hamburgerBtn" aria-label="Open menu">
        <span></span><span></span><span></span>
      </button>
    </div>
  `;

  const nav = document.querySelector('nav');
  if (nav) {
    nav.innerHTML = navHTML;

    
    const avatarBtn = document.getElementById('avatarBtn');
    const dropMenu  = document.getElementById('dropMenu');
    if (avatarBtn && dropMenu) {
      avatarBtn.addEventListener('click', e => { e.stopPropagation(); dropMenu.classList.toggle('show'); });
      document.addEventListener('click', () => dropMenu.classList.remove('show'));
    }

    // Mobile drawer
    _setupMobileDrawer(pages, activePage, student, initials);

    // Hamburger toggle
    const hamburger = document.getElementById('hamburgerBtn');
    if (hamburger) hamburger.addEventListener('click', _toggleMobileDrawer);
  }
}

function _setupMobileDrawer(pages, activePage, student, initials) {
  document.getElementById('mobileDrawer')?.remove();
  document.getElementById('mobileDrawerOverlay')?.remove();

  const drawer = document.createElement('div');
  drawer.id = 'mobileDrawer';
  drawer.className = 'mobile-drawer';
  drawer.innerHTML = `
    ${student ? `
      <div style="display:flex;align-items:center;gap:.75rem;padding:.75rem 1rem;margin-bottom:.75rem;background:var(--surface2);border-radius:9px;border:1px solid var(--border)">
        <div class="avatar" style="cursor:default;flex-shrink:0">${escapeHtml(initials)}</div>
        <div style="overflow:hidden">
          <div style="font-weight:600;font-size:.875rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(student.name || '')}</div>
          <div style="font-size:.72rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:'JetBrains Mono',monospace">${escapeHtml(student.email || '')}</div>
        </div>
      </div>
    ` : ''}
    <ul>
      ${pages.map(p => `<li><a href="${p.href}" class="${activePage === p.href ? 'active' : ''}">${escapeHtml(p.label)}</a></li>`).join('')}
      ${student ? `<li><a href="profile.html">My Profile</a></li><li><a href="#" onclick="logout();return false;" style="color:var(--danger)">Sign out</a></li>` : ''}
    </ul>
  `;

  const overlay = document.createElement('div');
  overlay.id = 'mobileDrawerOverlay';
  overlay.className = 'mobile-drawer-overlay';
  overlay.addEventListener('click', _closeMobileDrawer);

  document.body.appendChild(drawer);
  document.body.appendChild(overlay);
}

function _toggleMobileDrawer() {
  const drawer   = document.getElementById('mobileDrawer');
  const overlay  = document.getElementById('mobileDrawerOverlay');
  const hamburger = document.getElementById('hamburgerBtn');
  if (!drawer) return;
  const open = drawer.classList.toggle('open');
  overlay?.classList.toggle('open', open);
  hamburger?.classList.toggle('open', open);
}

function _closeMobileDrawer() {
  document.getElementById('mobileDrawer')?.classList.remove('open');
  document.getElementById('mobileDrawerOverlay')?.classList.remove('open');
  document.getElementById('hamburgerBtn')?.classList.remove('open');
}

function logout() {
  clearToken();
  window.location.href = 'login.html';
}


function buildRing(pct) {
  const r = 28, circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const color = pct >= 75 ? 'var(--success)' : pct >= 50 ? 'var(--accent)' : 'var(--danger)';
  return `
    <svg class="ring" viewBox="0 0 68 68">
      <circle class="ring-bg" cx="34" cy="34" r="${r}"/>
      <circle class="ring-fg" cx="34" cy="34" r="${r}"
        stroke="${color}"
        stroke-dasharray="${circ.toFixed(2)}"
        stroke-dashoffset="${offset.toFixed(2)}"/>
      <text class="score-text" x="34" y="34">${Math.round(pct)}%</text>
    </svg>`;
}

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
  if (Array.isArray(detail)) return detail.map(e => e.msg || JSON.stringify(e)).join('; ');
  return JSON.stringify(detail);
}

function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#039;');
}

function safePct(total, max) {
  if (!max || max === 0) return 0;
  return Math.round((total / max) * 100);
}


function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}