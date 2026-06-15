/* ═══════════════════════════════════════════
   TASKR — Frontend App Logic
   All CRUD operations via Flask REST API
   ═══════════════════════════════════════════ */

const API = '/api/todos';

// ── State ────────────────────────────────────
let state = {
  filter:   'all',
  priority: 'all',
  due:      'all',
  category: 'all',
  search:   '',
  editId:   null,
  editPriority: 'medium',
  sort: 'manual',
  calendar_date: '',
  lastAlertKey: '',
};

// ── DOM refs ──────────────────────────────────
const $list           = document.getElementById('todo-list');
const $empty          = document.getElementById('empty-state');
const $titleIn        = document.getElementById('todo-title');
const $descIn         = document.getElementById('todo-desc');
const $categoryIn     = document.getElementById('todo-category');
const $dueDateIn      = document.getElementById('todo-due-date');
const $addBtn         = document.getElementById('add-btn');
const $clearBtn       = document.getElementById('clear-btn');
const $searchIn       = document.getElementById('search-input');
const $categoryFilter = document.getElementById('category-filter');
const $priorityFilter = document.getElementById('priority-filter');
const $dueFilter      = document.getElementById('due-filter');
const $prioGroup      = document.getElementById('priority-group');
const $formError      = document.getElementById('form-error');
const $statTotal      = document.getElementById('stat-total');
const $statActive     = document.getElementById('stat-active');
const $statDone       = document.getElementById('stat-done');
const $dashPending    = document.getElementById('dash-pending');
const $dashCompleted  = document.getElementById('dash-completed');
const $dashPercent    = document.getElementById('dash-percent');
const $dashStreak     = document.getElementById('dash-streak');
const $progressText   = document.getElementById('progress-text');
const $progressFill   = document.getElementById('progress-fill');
const $alertPanel     = document.getElementById('alert-panel');
const $alertTitle     = document.getElementById('alert-title');
const $alertCount     = document.getElementById('alert-count');
const $alertCopy      = document.getElementById('alert-copy');
const $alertList      = document.getElementById('alert-list');
const $alertPermissionBtn = document.getElementById('alert-permission-btn');
const $chartBars      = document.getElementById('chart-bars');
const $sortFilter     = document.getElementById('sort-filter');
const $calendarDate   = document.getElementById('calendar-date');
const $themeToggle    = document.getElementById('theme-toggle');
const $header         = document.querySelector('.header');
const $headerUserName  = document.querySelector('.header__user-name');
const $profileBtn     = document.getElementById('profile-btn');
const $profileAvatar  = document.getElementById('profile-avatar');

// Modal
const $overlay        = document.getElementById('modal-overlay');
const $modalTitle     = document.getElementById('modal-title');
const $editTitle      = document.getElementById('edit-title');
const $editDesc       = document.getElementById('edit-desc');
const $editCategory   = document.getElementById('edit-category');
const $editDueDate    = document.getElementById('edit-due-date');
const $editPrioGroup  = document.getElementById('edit-priority-group');
const $modalSave      = document.getElementById('modal-save');
const $modalClose     = document.getElementById('modal-close');
const $modalCancel    = document.getElementById('modal-cancel');
const $modalError     = document.getElementById('modal-error');
const $profileOverlay = document.getElementById('profile-modal-overlay');
const $profileTitle   = document.getElementById('profile-modal-title');
const $profileName    = document.getElementById('profile-name');
const $profileEmail   = document.getElementById('profile-email');
const $profileContact = document.getElementById('profile-contact');
const $profileSave    = document.getElementById('profile-save');
const $profileClose   = document.getElementById('profile-modal-close');
const $profileCancel  = document.getElementById('profile-cancel');
const $profileError   = document.getElementById('profile-error');
const $toast          = document.getElementById('toast');

// ── Utilities ────────────────────────────────

function toast(msg, type = 'success') {
  $toast.textContent = msg;
  $toast.className   = `toast ${type} show`;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { $toast.className = 'toast'; }, 2500);
}

function showError($el, msg) {
  $el.textContent = msg;
  $el.hidden = false;
}
function clearError($el) { $el.hidden = true; }

function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: '2-digit' });
}

function fmtDateShort(isoDate) {
  if (!isoDate) return '';
  const d = new Date(`${isoDate}T00:00:00`);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
}

function dueLabel(todo) {
  if (!todo.due_date) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(`${todo.due_date}T00:00:00`);
  const diff = Math.round((due - today) / 86400000);

  if (diff < 0 && !todo.completed) return { text: 'overdue', cls: 'badge-due-overdue' };
  if (diff === 0) return { text: 'today', cls: 'badge-due-today' };
  if (diff === 1) return { text: 'tomorrow', cls: 'badge-due-upcoming' };
  return { text: `due ${fmtDateShort(todo.due_date)}`, cls: 'badge-due-upcoming' };
}

// ── Priority selector helper ──────────────────
function initPrioGroup($group, defaultP = 'medium') {
  $group.querySelectorAll('.prio-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.p === defaultP);
    btn.onclick = () => {
      $group.querySelectorAll('.prio-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    };
  });
}
function getActivePrio($group) {
  return ($group.querySelector('.prio-btn.active') || {}).dataset?.p || 'medium';
}

// ── Render ────────────────────────────────────
function renderCard(todo) {
  const due = dueLabel(todo);
  const card = document.createElement('div');
  card.className = `todo-card${todo.completed ? ' completed' : ''}`;
  card.dataset.id       = todo.id;
  card.dataset.priority = todo.priority;

  card.innerHTML = `
    <input type="checkbox" class="card-check" ${todo.completed ? 'checked' : ''} title="Toggle complete" />
    <div class="card-body">
      <div class="card-title">${escHtml(todo.title)}</div>
      ${todo.description ? `<div class="card-desc">${escHtml(todo.description)}</div>` : ''}
      <div class="card-meta">
        <span class="badge badge-${todo.priority}">${todo.priority}</span>
        <span class="badge badge-category">${escHtml(todo.category || 'general')}</span>
        ${due ? `<span class="badge ${due.cls}">${due.text}</span>` : ''}
        <span>${fmtDate(todo.created_at)}</span>
      </div>
    </div>
    <div class="card-actions">
      <button class="card-btn edit" title="Edit">✎</button>
      <button class="card-btn delete" title="Delete">✕</button>
    </div>`;

  // Toggle complete
  card.querySelector('.card-check').onchange = () => toggleComplete(todo.id, !todo.completed);

  // Edit
  card.querySelector('.card-btn.edit').onclick = () => openEditModal(todo);

  // Delete
  card.querySelector('.card-btn.delete').onclick = () => deleteTodo(todo.id);

  return card;
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function getProfileState() {
  return {
    name: $header?.dataset?.userName || $headerUserName?.textContent || 'Creator',
    email: $header?.dataset?.userEmail || '',
    contactNo: $header?.dataset?.userContact || '',
  };
}

function setProfileState(user) {
  if (!user) return;
  const name = user.name || 'Creator';
  const contactNo = user.contact_no || '';

  if ($header) {
    $header.dataset.userName = name;
    $header.dataset.userEmail = user.email || '';
    $header.dataset.userContact = contactNo;
  }

  if ($headerUserName) $headerUserName.textContent = name;
  if ($profileAvatar) $profileAvatar.textContent = name.trim().slice(0, 1).toUpperCase() || 'U';
}

function renderList(todos) {
  $list.innerHTML = '';
  if (!todos.length) {
    $empty.hidden = false;
    return;
  }
  $empty.hidden = true;
  todos.forEach(t => {
    const node = renderCard(t);
    node.draggable = true;
    node.ondragstart = (e) => { e.dataTransfer.setData('text/plain', t.id); };
    $list.appendChild(node);
  });

  $list.ondragover = (e) => { e.preventDefault(); };
  $list.ondrop = async (e) => {
    e.preventDefault();
    const draggedId = e.dataTransfer.getData('text/plain');
    if (!draggedId) return;
    // compute new order by current DOM order
    const ids = Array.from($list.querySelectorAll('.todo-card')).map(n => n.dataset.id);
    await reorder(ids);
    fetchTodos();
  };
}

async function reorder(ids) {
  try {
    const res = await fetch('/api/todos/reorder', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ ids })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to reorder');
    toast('Order saved');
  } catch (e) { toast(e.message, 'error'); }
}

function updateStats({ total, completed, active }) {
  $statTotal.textContent  = total;
  $statDone.textContent   = completed;
  $statActive.textContent = active;
}

function updateDashboard(stats) {
  $dashPending.textContent = stats.pending ?? stats.active ?? 0;
  $dashCompleted.textContent = stats.completed ?? 0;
  $dashPercent.textContent = (stats.completion_percent ?? 0) + '%';
  $dashStreak.textContent = (stats.streak ?? 0) + ' days';
  $progressText.textContent = `${stats.completed ?? 0}/${stats.total ?? 0} tasks`;
  const pct = stats.completion_percent ?? 0;
  if ($progressFill) $progressFill.style.width = `${pct}%`;
}

function alertSignature(items) {
  return items.map(item => item.id).join(',');
}

function notifyBrowser(title, body) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  try {
    new Notification(title, { body });
  } catch (error) {
    console.warn('Notification failed', error);
  }
}

function renderAlerts(alerts = {}) {
  if (!$alertPanel) return;

  const overdueTodos = Array.isArray(alerts.overdue_todos) ? alerts.overdue_todos : [];
  const overdueCount = Number(alerts.overdue_count ?? overdueTodos.length ?? 0);
  const key = alertSignature(overdueTodos);
  const changed = key !== state.lastAlertKey;

  state.lastAlertKey = key;

  if (!overdueCount) {
    $alertPanel.hidden = true;
    return;
  }

  $alertPanel.hidden = false;
  if ($alertTitle) $alertTitle.textContent = overdueCount === 1 ? '1 overdue task' : `${overdueCount} overdue tasks`;
  if ($alertCount) $alertCount.textContent = String(overdueCount);
  if ($alertCopy) {
    $alertCopy.textContent = overdueCount === 1
      ? 'This task has passed its due date and is still incomplete.'
      : 'These tasks have passed their due dates and are still incomplete.';
  }

  if ($alertList) {
    $alertList.innerHTML = '';
    overdueTodos.slice(0, 5).forEach(todo => {
      const item = document.createElement('li');
      const dueDate = todo.due_date ? fmtDateShort(todo.due_date) : 'no due date';
      item.textContent = `${todo.title} — due ${dueDate}`;
      $alertList.appendChild(item);
    });
  }

  if ($alertPermissionBtn) {
    const supported = 'Notification' in window;
    $alertPermissionBtn.hidden = !supported || Notification.permission === 'granted';
  }

  if (changed) {
    const title = overdueCount === 1 ? '1 overdue task' : `${overdueCount} overdue tasks`;
    const body = overdueTodos.slice(0, 3).map(todo => todo.title).join(', ');
    toast(title, 'error');
    notifyBrowser(title, body);
  }
}

function renderChart(chart) {
  if (!$chartBars) return;
  $chartBars.innerHTML = '';
  if (!Array.isArray(chart)) return;
  const max = Math.max(...chart.map(c => c.count), 1);
  chart.forEach(day => {
    const bar = document.createElement('div');
    bar.className = 'chart-bar';
    const h = Math.round((day.count / max) * 100);
    bar.style.height = `${Math.max(h, 8)}%`;
    bar.title = `${day.day}: ${day.count}`;
    const lbl = document.createElement('span'); lbl.textContent = day.count || '';
    bar.appendChild(lbl);
    $chartBars.appendChild(bar);
  });
}

// ── API calls ─────────────────────────────────

async function fetchTodos() {
  const params = new URLSearchParams({
    filter:   state.filter,
    priority: state.priority,
    due:      state.due,
    category: state.category,
    search:   state.search,
    sort:     state.sort,
    calendar_date: state.calendar_date,
  });
  try {
    const res  = await fetch(`${API}?${params}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to load');
    renderList(data.todos);
    updateStats(data.stats);
    updateDashboard(data.stats);
    renderAlerts(data.alerts || {});
    renderChart(data.chart || []);
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function createTodo() {
  clearError($formError);
  const title    = $titleIn.value.trim();
  const desc     = $descIn.value.trim();
  const category = ($categoryIn.value || '').trim();
  const dueDate  = $dueDateIn.value || null;
  const priority = getActivePrio($prioGroup);

  if (!title) { showError($formError, 'Please enter a title.'); return; }

  $addBtn.disabled = true;
  try {
    const res  = await fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description: desc, category, due_date: dueDate, priority }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to create');
    $titleIn.value = '';
    $descIn.value  = '';
    $categoryIn.value = '';
    $dueDateIn.value = '';
    initPrioGroup($prioGroup, 'medium');
    toast('Task added ✦');
    fetchTodos();
  } catch (e) {
    showError($formError, e.message);
  } finally {
    $addBtn.disabled = false;
  }
}

async function toggleComplete(id, completed) {
  try {
    const res  = await fetch(`${API}/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ completed }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    fetchTodos();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function deleteTodo(id) {
  try {
    const res  = await fetch(`${API}/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    toast('Task deleted');
    fetchTodos();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function saveEdit() {
  clearError($modalError);

  const title = $editTitle.value.trim();
  const desc = $editDesc.value.trim();
  const category = ($editCategory.value || '').trim();
  const dueDate = $editDueDate.value || null;
  const priority = getActivePrio($editPrioGroup);

  if (!title) {
    showError($modalError, 'Title cannot be empty.');
    return;
  }

  console.log("editId =", state.editId);
  console.log("Updating URL:", `${API}/${state.editId}`);

  $modalSave.disabled = true;

  try {
    const res = await fetch(`${API}/${state.editId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        title,
        description: desc,
        category,
        due_date: dueDate,
        priority
      })
    });

    const text = await res.text();
    console.log("Server Response:", text);

    let data;

    try {
      data = JSON.parse(text);
    } catch {
      throw new Error("Server returned HTML instead of JSON");
    }

    if (!res.ok) {
      throw new Error(data.error || 'Failed to update');
    }

    closeModal();
    toast('Task updated ✦');
    fetchTodos();

  } catch (e) {
    console.error(e);
    showError($modalError, e.message);
  } finally {
    $modalSave.disabled = false;
  }
}

async function clearCompleted() {
  try {
    const res  = await fetch(`${API}/completed`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    toast(data.message);
    fetchTodos();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function loadProfile() {
  try {
    const res = await fetch('/api/profile');
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to load profile');

    const user = data.user || {};
    if ($profileName) $profileName.value = user.name || '';
    if ($profileEmail) $profileEmail.value = user.email || '';
    if ($profileContact) $profileContact.value = user.contact_no || '';
    setProfileState(user);
  } catch (e) {
    toast(e.message, 'error');
  }
}

function openProfileModal() {
  clearError($profileError);
  loadProfile().finally(() => {
    if ($profileOverlay) {
      $profileOverlay.hidden = false;
      $profileName?.focus();
    }
  });
}

function closeProfileModal() {
  if ($profileOverlay) $profileOverlay.hidden = true;
}

async function saveProfile() {
  clearError($profileError);

  const name = ($profileName?.value || '').trim();
  const contactNo = ($profileContact?.value || '').trim();

  if (!name) {
    showError($profileError, 'Name cannot be empty.');
    return;
  }

  if ($profileSave) $profileSave.disabled = true;

  try {
    const res = await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, contact_no: contactNo }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to save profile');

    setProfileState(data.user || { name, contact_no: contactNo });
    closeProfileModal();
    toast('Profile updated ✦');
  } catch (e) {
    showError($profileError, e.message);
  } finally {
    if ($profileSave) $profileSave.disabled = false;
  }
}

// ── Modal helpers ─────────────────────────────
function openEditModal(todo) {
  console.log("Editing Todo:", todo);

  state.editId = todo.id;

  $editTitle.value = todo.title;
  $editDesc.value = todo.description || '';
  $editCategory.value = todo.category || 'general';
  $editDueDate.value = todo.due_date || '';

  initPrioGroup($editPrioGroup, todo.priority);

  clearError($modalError);

  $overlay.hidden = false;
  $editTitle.focus();
}

function closeModal() {
  $overlay.hidden  = true;
  state.editId     = null;
}

// ── Event listeners ───────────────────────────
$addBtn.onclick   = createTodo;
$clearBtn.onclick = clearCompleted;
$profileBtn?.addEventListener('click', openProfileModal);

$titleIn.onkeydown = e => { if (e.key === 'Enter') createTodo(); };

$searchIn.oninput = debounce(() => {
  state.search = $searchIn.value.trim();
  fetchTodos();
}, 300);

$categoryFilter.oninput = debounce(() => {
  const value = $categoryFilter.value.trim().toLowerCase();
  state.category = value || 'all';
  fetchTodos();
}, 300);

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.filter = btn.dataset.filter;
    fetchTodos();
  };
});

$priorityFilter.onchange = () => {
  state.priority = $priorityFilter.value;
  fetchTodos();
};

$dueFilter.onchange = () => {
  state.due = $dueFilter.value;
  fetchTodos();
};

$sortFilter?.addEventListener('change', () => {
  state.sort = $sortFilter.value;
  fetchTodos();
});

$calendarDate?.addEventListener('change', () => {
  state.calendar_date = $calendarDate.value || '';
  fetchTodos();
});

// Theme toggle
if ($themeToggle) {
  const stored = localStorage.getItem('taskr_theme');
  if (stored === 'dark') document.body.classList.add('theme-dark');
  $themeToggle.onclick = () => {
    const dark = document.body.classList.toggle('theme-dark');
    localStorage.setItem('taskr_theme', dark ? 'dark' : 'light');
  };
}

$modalSave.onclick   = saveEdit;
$modalClose.onclick  = closeModal;
$modalCancel.onclick = closeModal;
$overlay.onclick     = e => { if (e.target === $overlay) closeModal(); };

$profileSave?.addEventListener('click', saveProfile);
$profileClose?.addEventListener('click', closeProfileModal);
$profileCancel?.addEventListener('click', closeProfileModal);
$profileOverlay?.addEventListener('click', e => { if (e.target === $profileOverlay) closeProfileModal(); });

if ($alertPermissionBtn) {
  $alertPermissionBtn.onclick = async () => {
    if (!('Notification' in window)) {
      toast('Browser notifications are not supported here.', 'error');
      return;
    }

    try {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        toast('Browser alerts enabled');
        renderAlerts({ overdue_count: 0, overdue_todos: [] });
        fetchTodos();
      } else {
        toast('Browser alerts were not enabled.', 'error');
      }
    } catch (error) {
      toast(error.message, 'error');
    }
  };
}

document.onkeydown = e => {
  if (e.key !== 'Escape') return;
  if ($overlay && !$overlay.hidden) closeModal();
  if ($profileOverlay && !$profileOverlay.hidden) closeProfileModal();
};

$editTitle.onkeydown = e => { if (e.key === 'Enter') saveEdit(); };
$profileName?.addEventListener('keydown', e => { if (e.key === 'Enter') saveProfile(); });
$profileContact?.addEventListener('keydown', e => { if (e.key === 'Enter') saveProfile(); });

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ── Init ──────────────────────────────────────
initPrioGroup($prioGroup, 'medium');
setProfileState(getProfileState());
fetchTodos();
setInterval(fetchTodos, 60000);
