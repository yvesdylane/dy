from fastapi import APIRouter, Query

router = APIRouter()


APP_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 50: '#fffbeb', 100: '#fef3c7', 200: '#fde68a', 300: '#fcd34d',
                     400: '#fbbf24', 500: '#f59e0b', 600: '#d97706', 700: '#b45309',
                     800: '#92400e', 900: '#78350f' }
          }
        }
      }
    }
  </script>
  <title>dy</title>
</head>
<body class="bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 min-h-[100dvh] transition-colors duration-200">

<div id="loadingView" class="flex items-center justify-center min-h-[90dvh]">
  <div class="animate-spin h-8 w-8 border-4 border-brand-500 border-t-transparent rounded-full"></div>
</div>

<div id="registerView" class="hidden max-w-md mx-auto p-4 space-y-5">
  <h2 class="text-xl font-bold text-brand-600 dark:text-brand-400">Create Account</h2>

  <form id="registerForm" onsubmit="return false" class="space-y-3">
    <label class="block text-sm font-medium">Name <input name="name" required
      class="mt-1 w-full px-3 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"></label>
    <label class="block text-sm font-medium">Surname <input name="surname" required
      class="mt-1 w-full px-3 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"></label>
    <label class="block text-sm font-medium">Phone (+237) <input name="phone" placeholder="+237XXXXXXXXX" required
      class="mt-1 w-full px-3 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"></label>
    <label class="block text-sm font-medium">Gender
      <select name="gender" required
        class="mt-1 w-full px-3 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none">
        <option value="">--</option><option value="male">Male</option><option value="female">Female</option>
      </select></label>
    <label class="block text-sm font-medium">Department
      <select name="department" required
        class="mt-1 w-full px-3 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none">
        <option value="">--</option>
        <option value="ISM">ISM</option><option value="SWE">SWE</option><option value="CGWD">CGWD</option>
        <option value="EDM">EDM</option><option value="CNWS">CNWS</option><option value="NS">NS</option>
      </select></label>
    <label class="block text-sm font-medium">Group
      <select name="group"
        class="mt-1 w-full px-3 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none">
        <option value="">None</option><option value="A">A</option><option value="B">B</option>
      </select></label>
    <label class="block text-sm font-medium">School <input name="school" required
      class="mt-1 w-full px-3 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"></label>
    <label class="block text-sm font-medium">Date of Birth <input name="dob" type="date" required
      class="mt-1 w-full px-3 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"></label>
    <p id="errorMsg" class="text-red-500 text-sm hidden"></p>
    <button type="submit"
      class="w-full py-3 rounded-lg bg-brand-500 hover:bg-brand-600 text-white font-semibold text-sm transition-colors">Register</button>
  </form>
</div>

  <div id="adminView" class="hidden flex min-h-screen">
    <div class="hidden md:flex md:flex-col md:w-56 md:bg-zinc-50 md:dark:bg-zinc-900 md:border-r md:border-zinc-200 md:dark:border-zinc-800 md:fixed md:h-full">
      <div class="p-4 border-b border-zinc-200 dark:border-zinc-800">
        <h2 class="font-bold text-brand-600 dark:text-brand-400">dy</h2>
        <p id="adminNameSide" class="text-xs text-zinc-500 mt-1"></p>
      </div>
      <nav class="flex-1 p-2 space-y-1">
        <button data-section="stats" class="nav-btn w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-brand-100 dark:hover:bg-brand-950">📊 Stats</button>
        <button data-section="users" class="nav-btn w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-brand-100 dark:hover:bg-brand-950">👥 Users</button>
        <button data-section="codes" class="nav-btn w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-brand-100 dark:hover:bg-brand-950">🔑 Codes</button>
      </nav>
    </div>
    <div class="flex-1 md:ml-56 min-w-0">
      <div class="md:hidden flex items-center gap-2 p-4 border-b border-zinc-200 dark:border-zinc-800">
        <div class="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center text-white font-bold text-sm">D</div>
        <div><h1 class="font-bold text-sm">Dashboard</h1><p id="adminNameMobile" class="text-xs text-zinc-500"></p></div>
      </div>
      <div class="p-4 pb-24 md:pb-4">
        <div id="sectionStats">
          <div id="statsGrid" class="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div class="p-4 rounded-xl bg-brand-50 dark:bg-brand-950 border border-brand-200 dark:border-brand-900">
              <p class="text-xs uppercase tracking-wider text-brand-700 dark:text-brand-400 font-medium">Total Users</p>
              <p id="statUsers" class="text-3xl font-bold mt-1 text-zinc-900 dark:text-white">--</p>
            </div>
            <div class="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <p class="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 font-medium">Interns</p>
              <p id="statInterns" class="text-3xl font-bold mt-1 text-zinc-900 dark:text-white">--</p>
            </div>
            <div class="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <p class="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 font-medium">Instructors</p>
              <p id="statInstructors" class="text-3xl font-bold mt-1 text-zinc-900 dark:text-white">--</p>
            </div>
            <div class="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
              <p class="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 font-medium">Tasks</p>
              <p id="statTasks" class="text-3xl font-bold mt-1 text-zinc-900 dark:text-white">--</p>
            </div>
            <div class="p-4 rounded-xl bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-900">
              <p class="text-xs uppercase tracking-wider text-green-700 dark:text-green-400 font-medium">Total Fees</p>
              <p id="statTotalFees" class="text-2xl font-bold mt-1 text-zinc-900 dark:text-white">--</p>
            </div>
            <div class="p-4 rounded-xl bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-900">
              <p class="text-xs uppercase tracking-wider text-green-700 dark:text-green-400 font-medium">Paid</p>
              <p id="statPaid" class="text-2xl font-bold mt-1 text-zinc-900 dark:text-white">--</p>
            </div>
          </div>
        </div>
      <div id="sectionUsers" class="hidden">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold">Users</h3>
          <button id="addUserBtn" class="px-3 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium">+ Add</button>
        </div>
        <div class="flex flex-wrap gap-2 mb-3">
          <input id="userSearch" placeholder="Search name/phone..."
            class="w-full sm:flex-1 px-3 py-1.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-xs outline-none focus:ring-2 focus:ring-brand-500">
          <select id="userDeptFilter"
            class="px-2 py-1.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-xs outline-none focus:ring-2 focus:ring-brand-500">
            <option value="">All depts</option>
            <option value="ISM">ISM</option><option value="SWE">SWE</option><option value="CGWD">CGWD</option>
            <option value="EDM">EDM</option><option value="CNWS">CNWS</option><option value="NS">NS</option>
          </select>
          <select id="userRoleFilter"
            class="px-2 py-1.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-xs outline-none focus:ring-2 focus:ring-brand-500">
            <option value="">All roles</option>
            <option value="admin">Admin</option><option value="instructor">Instructor</option><option value="intern">Intern</option>
          </select>
        </div>
        <div id="usersList" class="space-y-2"></div>
      </div>
      <div id="sectionCodes" class="hidden">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold">Codes</h3>
          <button id="addCodeBtn" class="px-3 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium">+ Generate</button>
        </div>
        <div id="codesList" class="space-y-2"></div>
      </div>
    </div>
  </div>
  <div id="modalOverlay" class="hidden fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
    <div id="modalContent" class="bg-white dark:bg-zinc-900 rounded-xl w-full max-w-md max-h-[85vh] overflow-y-auto p-5 space-y-4"></div>
  </div>
  <div class="md:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-800 flex safe-area-bottom">
    <button data-section="stats" class="nav-btn flex-1 py-3 text-center text-xs font-medium">📊 Stats</button>
    <button data-section="users" class="nav-btn flex-1 py-3 text-center text-xs font-medium">👥 Users</button>
    <button data-section="codes" class="nav-btn flex-1 py-3 text-center text-xs font-medium">🔑 Codes</button>
  </div>
</div>

<div id="welcomeView" class="hidden max-w-md mx-auto p-4 text-center space-y-4">
  <div class="text-5xl mt-16 mb-4">👋</div>
  <h2 class="text-xl font-bold" id="welcomeName"></h2>
  <p class="text-sm text-zinc-500 dark:text-zinc-400">You're registered. Use bot commands like /info to view your data.</p>
</div>

<script>
(function() {
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg) tg.ready();

  const cs = tg ? tg.colorScheme : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.classList.toggle('dark', cs === 'dark');

  const show = (id) => {
    ['loadingView','registerView','adminView','welcomeView'].forEach(v =>
      document.getElementById(v).classList.toggle('hidden', v !== id));
  };

  let tid = null;

  const params = new URLSearchParams(window.location.search);
  const urlTid = params.get('telegram_id');
  if (urlTid) {
    tid = urlTid;
  } else if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
    tid = String(tg.initDataUnsafe.user.id);
  }

  const nameEl = (id) => document.getElementById(id);
  const esc = (s) => { const d=document.createElement('div'); d.textContent=s; return d.innerHTML; };

  function showSection(name) {
    ['sectionStats','sectionUsers','sectionCodes'].forEach(s =>
      nameEl(s).classList.toggle('hidden', s !== 'section' + name[0].toUpperCase() + name.slice(1)));
  }

  async function loadStats() {
    const s = await (await fetch('/api/admin/stats?telegram_id=' + encodeURIComponent(tid))).json();
    if (s.ok) {
      nameEl('statUsers').textContent = s.total_users;
      nameEl('statInterns').textContent = s.interns;
      nameEl('statInstructors').textContent = s.instructors;
      nameEl('statTasks').textContent = s.tasks;
      nameEl('statTotalFees').textContent = Number(s.total_fees).toLocaleString();
      nameEl('statPaid').textContent = Number(s.total_paid).toLocaleString() + ' / ' + Number(s.total_fees).toLocaleString();
    }
  }

  let allUsers = [];

  function filterUsers() {
    const q = nameEl('userSearch').value.toLowerCase();
    const dept = nameEl('userDeptFilter').value;
    const role = nameEl('userRoleFilter').value;
    return allUsers.filter(u =>
      (u.name.toLowerCase().includes(q) || u.surname.toLowerCase().includes(q) || u.phone.includes(q)) &&
      (!dept || u.department === dept) &&
      (!role || u.role === role)
    );
  }

  function renderUsers() {
    const list = nameEl('usersList');
    const filtered = filterUsers();
    list.innerHTML = filtered.map(u => `
      <div class="user-row p-3 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex items-center justify-between cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-850 transition-colors" data-id="${u.id}">
        <div class="min-w-0 flex-1">
          <p class="font-medium text-sm truncate">${u.name} ${u.surname}</p>
          <p class="text-xs text-zinc-500">${u.department} · ${u.role} · ${u.phone} · ${u.linked ? 'linked' : 'pending'}</p>
        </div>
        <span class="text-xs px-2 py-0.5 rounded-full ${u.role === 'admin' ? 'bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300' : u.role === 'instructor' ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300' : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300'}">${u.role}</span>
      </div>
    `).join('');
  }

  async function loadUsers() {
    const r = await (await fetch('/api/admin/users?telegram_id=' + encodeURIComponent(tid))).json();
    if (!r.ok) return;
    allUsers = r.users;
    renderUsers();
  }

  async function loadCodes() {
    const r = await (await fetch('/api/admin/codes?telegram_id=' + encodeURIComponent(tid))).json();
    if (!r.ok) return;
    const list = nameEl('codesList');
    list.innerHTML = r.codes.map(c => `
      <div class="p-3 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex items-center justify-between">
        <div>
          <p class="font-mono text-sm">${c.code}</p>
          <p class="text-xs text-zinc-500">${c.is_used ? 'Used' : 'Available'} · ${c.role}</p>
        </div>
        <button class="del-code-btn ml-2 p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg text-xs" data-id="${c.id}">✕</button>
      </div>
    `).join('');
  }

  async function checkAndShow(idToCheck) {
    try {
      const me = await (await fetch('/api/me?telegram_id=' + encodeURIComponent(idToCheck))).json();
      if (!me.exists) { show('registerView'); return; }
      if (me.role === 'admin') {
        const fullName = me.name + ' ' + me.surname;
        nameEl('adminNameSide').textContent = fullName;
        nameEl('adminNameMobile').textContent = fullName;
        show('adminView');
        await loadStats();
        showSection('stats');

        document.querySelectorAll('.nav-btn').forEach(b =>
          b.addEventListener('click', async () => {
            const section = b.dataset.section;
            showSection(section);
            if (section === 'users') await loadUsers();
            if (section === 'codes') await loadCodes();
          })
        );

        nameEl('addUserBtn').addEventListener('click', () => showUserForm());
        nameEl('addCodeBtn').addEventListener('click', () => showCodeForm());

        nameEl('userSearch').addEventListener('input', renderUsers);
        nameEl('userDeptFilter').addEventListener('change', renderUsers);
        nameEl('userRoleFilter').addEventListener('change', renderUsers);

        nameEl('usersList').addEventListener('click', (e) => {
          const row = e.target.closest('.user-row');
          if (row) {
            const u = allUsers.find(x => x.id == row.dataset.id);
            if (u) showUserDetail(u);
          }
        });

        document.addEventListener('click', async (e) => {
          const d = e.target.closest('.del-code-btn');
          if (d && confirm('Delete this code?')) {
            await fetch('/api/admin/codes/' + d.dataset.id + '?telegram_id=' + encodeURIComponent(tid), {method:'DELETE'});
            await loadCodes();
          }
        });
      } else {
        nameEl('welcomeName').textContent = 'Welcome back, ' + me.name + '!';
        show('welcomeView');
      }
    } catch(e) {
      show('registerView');
    }
  }

  function showUserForm(data) {
    const m = nameEl('modalOverlay');
    const c = nameEl('modalContent');
    const isEdit = !!data;
    c.innerHTML = `
      <h3 class="font-bold text-lg">${isEdit ? 'Edit' : 'Add'} User</h3>
      <form id="userForm" class="space-y-3" onsubmit="return false">
        <input name="name" placeholder="Name" value="${isEdit ? esc(data.name) : ''}" required
          class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">
        <input name="surname" placeholder="Surname" value="${isEdit ? esc(data.surname) : ''}" required
          class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">
        <input name="phone" placeholder="Phone (+237XXXXXXXXX)" value="${isEdit ? esc(data.phone) : ''}" required
          class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">
        <select name="gender" required
          class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">
          <option value="">Gender</option>
          <option value="male" ${isEdit && data.gender === 'male' ? 'selected' : ''}>Male</option>
          <option value="female" ${isEdit && data.gender === 'female' ? 'selected' : ''}>Female</option>
        </select>
        <select name="department" required
          class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">
          <option value="">Department</option>
          ${['ISM','SWE','CGWD','EDM','CNWS','NS'].map(d =>
            `<option value="${d}" ${isEdit && data.department === d ? 'selected' : ''}>${d}</option>`).join('')}
        </select>
        <select name="group"
          class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">
          <option value="">Group</option>
          <option value="A" ${isEdit && data.group === 'A' ? 'selected' : ''}>A</option>
          <option value="B" ${isEdit && data.group === 'B' ? 'selected' : ''}>B</option>
        </select>
        <input name="school" placeholder="School" value="${isEdit ? esc(data.school) : ''}" required
          class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">
        <input name="dob" type="date" value="${isEdit ? data.dob : ''}" required
          class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">
        ${isEdit ? '<select name="role" class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500"><option value="">Role</option><option value="intern" ' + (data.role === 'intern' ? 'selected' : '') + '>Intern</option><option value="instructor" ' + (data.role === 'instructor' ? 'selected' : '') + '>Instructor</option><option value="admin" ' + (data.role === 'admin' ? 'selected' : '') + '>Admin</option></select>' : ''}
        ${isEdit ? '<input name="total_fees" type="number" step="0.01" placeholder="Total fees" value="' + (data.total_fees || 0) + '" class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">' : ''}
        ${isEdit ? '<input name="fees_paid" type="number" step="0.01" placeholder="Fees paid" value="' + (data.fees_paid || 0) + '" class="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">' : ''}
        <p id="userFormErr" class="text-red-500 text-xs hidden"></p>
        <div class="flex gap-2">
          <button type="button" id="modalCancel"
            class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium">Cancel</button>
          <button type="submit"
            class="flex-1 py-2.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium">${isEdit ? 'Save' : 'Create'}</button>
        </div>
      </form>`;
    m.classList.remove('hidden');

    nameEl('modalCancel').onclick = () => m.classList.add('hidden');
    m.onclick = (e) => { if (e.target === m) m.classList.add('hidden'); };

    nameEl('userForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const f = e.target;
      const g = (n) => f.elements[n];
      const body = { name: g('name').value, surname: g('surname').value, phone: g('phone').value,
        gender: g('gender').value, department: g('department').value, group: g('group').value || null,
        school: g('school').value, dob: g('dob').value };
      if (isEdit) {
        if (g('role')) body.role = g('role').value;
        if (g('total_fees')) body.total_fees = parseFloat(g('total_fees').value) || 0;
        if (g('fees_paid')) body.fees_paid = parseFloat(g('fees_paid').value) || 0;
      }
      const url = isEdit
        ? '/api/admin/users/' + data.id + '?telegram_id=' + encodeURIComponent(tid)
        : '/api/admin/users?telegram_id=' + encodeURIComponent(tid);
      const method = isEdit ? 'PUT' : 'POST';
      const r = await (await fetch(url, {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})).json();
      if (r.ok) { m.classList.add('hidden'); await loadUsers(); }
      else { const err = nameEl('userFormErr'); err.textContent = r.detail; err.classList.remove('hidden'); }
    });
  }

  function showUserDetail(u) {
    const m = nameEl('modalOverlay');
    const c = nameEl('modalContent');
    c.innerHTML = `
      <h3 class="font-bold text-lg">${esc(u.name)} ${esc(u.surname)}</h3>
      <div class="space-y-2 text-sm">
        <div class="grid grid-cols-2 gap-2">
          <div><span class="text-zinc-500">Role</span><p class="font-medium">${u.role}</p></div>
          <div><span class="text-zinc-500">Department</span><p class="font-medium">${u.department}</p></div>
          <div><span class="text-zinc-500">Gender</span><p class="font-medium">${u.gender}</p></div>
          <div><span class="text-zinc-500">Group</span><p class="font-medium">${u.group || '—'}</p></div>
          <div><span class="text-zinc-500">Phone</span><p class="font-medium">${esc(u.phone)}</p></div>
          <div><span class="text-zinc-500">School</span><p class="font-medium">${esc(u.school)}</p></div>
          <div><span class="text-zinc-500">DOB</span><p class="font-medium">${u.dob}</p></div>
          <div><span class="text-zinc-500">Status</span><p class="font-medium">${u.linked ? 'Linked' : 'Pending'}</p></div>
          <div><span class="text-zinc-500">Total Fees</span><p class="font-medium">${Number(u.total_fees || 0).toLocaleString()}</p></div>
          <div><span class="text-zinc-500">Paid</span><p class="font-medium" class="${u.fees_paid >= u.total_fees ? 'text-green-600 dark:text-green-400' : 'text-brand-600 dark:text-brand-400'}">${Number(u.fees_paid || 0).toLocaleString()}</p></div>
        </div>
      </div>
      <div class="flex gap-2 pt-2">
        <button type="button" id="modalEditUser" class="flex-1 py-2.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium">Edit</button>
        <button type="button" id="modalDeleteUser" class="flex-1 py-2.5 rounded-lg border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 text-sm font-medium">Delete</button>
        <button type="button" id="modalClose" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium">Close</button>
      </div>`;
    m.classList.remove('hidden');
    nameEl('modalClose').onclick = () => m.classList.add('hidden');
    nameEl('modalEditUser').onclick = () => { m.classList.add('hidden'); showUserForm(u); };
    nameEl('modalDeleteUser').onclick = async () => {
      if (!confirm("Delete " + esc(u.name) + " " + esc(u.surname) + "?")) return;
      await fetch('/api/admin/users/' + u.id + '?telegram_id=' + encodeURIComponent(tid), {method:'DELETE'});
      m.classList.add('hidden');
      await loadUsers();
    };
    m.onclick = (e) => { if (e.target === m) m.classList.add('hidden'); };
  }

  function showCodeForm() {
    const m = nameEl('modalOverlay');
    const c = nameEl('modalContent');
    c.innerHTML = '<h3 class="font-bold text-lg">Generate Code</h3>' +
      '<form id="codeForm" class="space-y-3" onsubmit="return false">' +
      '<label class="block text-sm font-medium">Role' +
      '<select name="role" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500">' +
      '<option value="intern">Intern</option><option value="instructor">Instructor</option><option value="admin">Admin</option></select></label>' +
      '<label class="block text-sm font-medium">Expires in (minutes)' +
      '<input name="expiry" type="number" value="60" min="1" required class="mt-1 w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-sm outline-none focus:ring-2 focus:ring-brand-500"></label>' +
      '<p id="codeFormErr" class="text-red-500 text-xs hidden"></p>' +
      '<div class="flex gap-2">' +
      '<button type="button" id="modalCancel" class="flex-1 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 text-sm font-medium">Cancel</button>' +
      '<button type="submit" class="flex-1 py-2.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium">Generate</button></div></form>';
    m.classList.remove('hidden');
    nameEl('modalCancel').onclick = () => m.classList.add('hidden');
    m.onclick = (e) => { if (e.target === m) m.classList.add('hidden'); };
    nameEl('codeForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const f = e.target;
      const g = (n) => f.elements[n];
      const body = { role: g('role').value, expiry_minutes: parseInt(g('expiry').value) || 60 };
      const r = await (await fetch('/api/admin/codes?telegram_id=' + encodeURIComponent(tid),
        {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})).json();
      if (r.ok) { m.classList.add('hidden'); await loadCodes(); }
      else { const err = nameEl('codeFormErr'); err.textContent = r.detail; err.classList.remove('hidden'); }
    });
  }

  (async () => {
    if (tid) { await checkAndShow(tid); return; }
    show('registerView');
  })();

  const form = document.getElementById('registerForm');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const err = document.getElementById('errorMsg');
      err.style.display = 'none';
      if (!tid) { err.textContent = 'Telegram ID not available — open this page from Telegram'; err.style.display = 'block'; return; }
      const data = {
        name: form.name.value, surname: form.surname.value, phone: form.phone.value,
        telegram_id: tid, gender: form.gender.value, department: form.department.value,
        group: form.group.value || null, school: form.school.value, dob: form.dob.value,
      };
      try {
        const res = await (await fetch('/api/register', { method:'POST',
          headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) })).json();
        if (res.ok) {
          if (tg) { tg.HapticFeedback?.notificationOccurred?.('success'); tg.close(); }
          else location.reload();
        } else {
          err.textContent = res.detail; err.style.display = 'block';
        }
      } catch(e) {
        err.textContent = 'Network error'; err.style.display = 'block';
      }
      return false;
    });
  }
})();
</script>
</body>
</html>"""


@router.get("/app")
async def mini_app():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(APP_HTML)


@router.get("/api/me")
async def get_me(telegram_id: str = Query(...)):
    import logging

    from sqlalchemy import select

    from db.database import async_session
    from models.models import User

    logger = logging.getLogger("api.me")
    logger.info("Lookup – telegram_id: %s", telegram_id)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

    if not user:
        logger.info("User not found")
        return {"exists": False}
    logger.info("Found user: %s %s, role: %s", user.name, user.surname, user.role.value)
    return {
        "exists": True,
        "id": user.id,
        "name": user.name,
        "surname": user.surname,
        "role": user.role.value,
    }


@router.get("/api/admin/stats")
async def admin_stats(telegram_id: str = Query(...)):
    from sqlalchemy import func, select

    from db.database import async_session
    from models.models import Role, Task, User

    async with async_session() as session:
        admin_user = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin_user.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        total_users = (await session.execute(select(func.count(User.id)))).scalar()
        interns = (await session.execute(
            select(func.count(User.id)).where(User.role == Role.intern)
        )).scalar()
        instructors = (await session.execute(
            select(func.count(User.id)).where(User.role == Role.instructor)
        )).scalar()
        tasks = (await session.execute(select(func.count(Task.id)))).scalar()
        total_fees = (await session.execute(select(func.sum(User.total_fees)))).scalar() or 0
        total_paid = (await session.execute(select(func.sum(User.fees_paid)))).scalar() or 0

    total_fees = float(total_fees)
    total_paid = float(total_paid)
    return {"ok": True, "total_users": total_users, "interns": interns,
        "instructors": instructors, "tasks": tasks,
        "total_fees": total_fees, "total_paid": total_paid, "outstanding": total_fees - total_paid}


@router.get("/api/admin/users")
async def admin_list_users(telegram_id: str = Query(...)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Role, User

    async with async_session() as session:
        admin = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        users = (await session.execute(select(User).order_by(User.id))).scalars().all()

    return {"ok": True, "users": [{
        "id": u.id, "name": u.name, "surname": u.surname, "phone": u.phone,
        "telegram_id": u.telegram_id, "gender": u.gender.value,
        "role": u.role.value, "department": u.department.value,
        "group": u.group.value if u.group else None,
        "school": u.school, "dob": str(u.dob),
        "linked": not u.telegram_id.startswith("pending_"),
        "fees_paid": float(u.fees_paid) if u.fees_paid else 0,
        "total_fees": float(u.total_fees) if u.total_fees else 0,
    } for u in users]}


@router.post("/api/admin/users")
async def admin_create_user(telegram_id: str = Query(...), data: dict = None):
    from datetime import datetime
    from uuid import uuid4

    from sqlalchemy import select

    from db.database import async_session
    from models.models import Department, Gender, Group, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            existing_phone = await session.execute(
                select(User).where(User.phone == data["phone"])
            )
            if existing_phone.scalar_one_or_none():
                return {"ok": False, "detail": "Phone already exists"}

            placeholder = f"pending_{uuid4().hex[:12]}"
            user = User(
                name=data["name"], surname=data["surname"], phone=data["phone"],
                telegram_id=placeholder, gender=Gender(data["gender"]),
                role=Role.intern, department=Department(data["department"]),
                group=Group(data["group"]) if data.get("group") else None,
                school=data["school"],
                dob=datetime.strptime(data["dob"], "%Y-%m-%d").date(),
            )
            session.add(user)

    return {"ok": True, "user": {
        "id": user.id, "name": user.name, "surname": user.surname,
        "phone": user.phone, "gender": user.gender.value,
        "department": user.department.value, "group": user.group.value if user.group else None,
        "school": user.school, "dob": str(user.dob),
    }}


@router.put("/api/admin/users/{user_id}")
async def admin_update_user(user_id: int, telegram_id: str = Query(...), data: dict = None):
    from datetime import datetime

    from sqlalchemy import select

    from db.database import async_session
    from models.models import Department, Gender, Group, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            user = await session.get(User, user_id)
            if not user:
                return {"ok": False, "detail": "User not found"}

            if "name" in data: user.name = data["name"]
            if "surname" in data: user.surname = data["surname"]
            if "phone" in data:
                dup = await session.execute(
                    select(User).where(User.phone == data["phone"], User.id != user_id)
                )
                if dup.scalar_one_or_none():
                    return {"ok": False, "detail": "Phone already in use"}
                user.phone = data["phone"]
            if "gender" in data: user.gender = Gender(data["gender"])
            if "role" in data: user.role = Role(data["role"])
            if "department" in data: user.department = Department(data["department"])
            if "group" in data: user.group = Group(data["group"]) if data["group"] else None
            if "school" in data: user.school = data["school"]
            if "dob" in data: user.dob = datetime.strptime(data["dob"], "%Y-%m-%d").date()
            if "fees_paid" in data: user.fees_paid = float(data["fees_paid"])
            if "total_fees" in data: user.total_fees = float(data["total_fees"])

    return {"ok": True}


@router.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: int, telegram_id: str = Query(...)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            user = await session.get(User, user_id)
            if not user:
                return {"ok": False, "detail": "User not found"}

            await session.delete(user)

    return {"ok": True}


@router.get("/api/admin/codes")
async def admin_list_codes(telegram_id: str = Query(...)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import CreationCode, Role, User

    async with async_session() as session:
        admin = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        codes = (await session.execute(
            select(CreationCode).order_by(CreationCode.created_at.desc())
        )).scalars().all()

    return {"ok": True, "codes": [{
        "id": c.id, "code": c.code, "role": c.role.value,
        "is_used": c.is_used, "created_at": str(c.created_at),
        "expires_at": str(c.expires_at),
    } for c in codes]}


@router.post("/api/admin/codes")
async def admin_create_code(telegram_id: str = Query(...), data: dict = None):
    import random
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from db.database import async_session
    from models.models import CreationCode, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            admin_user = admin.scalar_one_or_none()
            if not admin_user:
                return {"ok": False, "detail": "Unauthorized"}

            code = str(random.randint(100000, 999999))
            while True:
                exists = await session.execute(
                    select(CreationCode).where(CreationCode.code == code)
                )
                if not exists.scalar_one_or_none():
                    break
                code = str(random.randint(100000, 999999))

            role_val = data.get("role", "intern") if data else "intern"
            expiry_minutes = data.get("expiry_minutes", 60) if data else 60

            cc = CreationCode(
                code=code, role=Role(role_val),
                expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes),
                created_by=admin_user.id,
            )
            session.add(cc)

    return {"ok": True, "code": {"id": cc.id, "code": cc.code, "role": cc.role.value}}


@router.delete("/api/admin/codes/{code_id}")
async def admin_delete_code(code_id: int, telegram_id: str = Query(...)):
    from sqlalchemy import select
    from db.database import async_session
    from models.models import CreationCode, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            cc = await session.get(CreationCode, code_id)
            if not cc:
                return {"ok": False, "detail": "Code not found"}

            await session.delete(cc)

    return {"ok": True}


@router.post("/api/register")
async def register(data: dict):
    from datetime import datetime

    from sqlalchemy import select

    from db.database import async_session
    from models.models import Department, Gender, Group, Role, User

    try:
        async with async_session() as session:
            async with session.begin():
                existing = await session.execute(
                    select(User).where(User.telegram_id == data["telegram_id"])
                )
                if existing.scalar_one_or_none():
                    return {"ok": False, "detail": "User already registered"}

                session.add(User(
                    name=data["name"], surname=data["surname"], phone=data["phone"],
                    telegram_id=data["telegram_id"], gender=Gender(data["gender"]),
                    role=Role.intern, department=Department(data["department"]),
                    group=Group(data["group"]) if data.get("group") else None,
                    school=data["school"],
                    dob=datetime.strptime(data["dob"], "%Y-%m-%d").date(),
                ))

        return {"ok": True}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
