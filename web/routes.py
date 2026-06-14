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

<div id="adminView" class="hidden max-w-2xl mx-auto p-4 space-y-5">
  <div class="flex items-center gap-3 pb-2 border-b border-zinc-200 dark:border-zinc-800">
    <div class="w-10 h-10 rounded-xl bg-brand-500 flex items-center justify-center text-white font-bold text-lg">D</div>
    <div><h1 class="text-xl font-bold">Admin Dashboard</h1><p id="adminName" class="text-sm text-zinc-500 dark:text-zinc-400"></p></div>
  </div>
  <div id="statsGrid" class="grid grid-cols-2 gap-3">
    <div class="p-4 rounded-xl bg-brand-50 dark:bg-brand-950 border border-brand-200 dark:border-brand-900">
      <p class="text-xs uppercase tracking-wider text-brand-700 dark:text-brand-400 font-medium">Total Users</p>
      <p id="statUsers" class="text-3xl font-bold mt-1">--</p>
    </div>
    <div class="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
      <p class="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 font-medium">Interns</p>
      <p id="statInterns" class="text-3xl font-bold mt-1">--</p>
    </div>
    <div class="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
      <p class="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 font-medium">Instructors</p>
      <p id="statInstructors" class="text-3xl font-bold mt-1">--</p>
    </div>
    <div class="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
      <p class="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 font-medium">Tasks</p>
      <p id="statTasks" class="text-3xl font-bold mt-1">--</p>
    </div>
  </div>
  <div class="space-y-2">
    <h3 class="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Quick Actions</h3>
    <div class="grid grid-cols-2 gap-2">
      <button onclick="tg?.HapticFeedback?.impactOccurred('light')"
        class="py-3 px-4 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium transition-colors">+ Create Code</button>
      <button onclick="tg?.HapticFeedback?.impactOccurred('light')"
        class="py-3 px-4 rounded-xl border border-zinc-300 dark:border-zinc-700 text-sm font-medium transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800">View Users</button>
    </div>
  </div>
</div>

<div id="welcomeView" class="hidden max-w-md mx-auto p-4 text-center space-y-4">
  <div class="text-5xl mt-16 mb-4">👋</div>
  <h2 class="text-xl font-bold" id="welcomeName"></h2>
  <p class="text-sm text-zinc-500 dark:text-zinc-400">You're registered. Use bot commands like /info to view your data.</p>
</div>

<div id="debugView" class="fixed bottom-0 left-0 right-0 p-2 bg-zinc-900/80 text-zinc-300 text-xs font-mono leading-relaxed hidden">
  <p id="debugInfo"></p>
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

  const dbg = (msg) => {
    const el = document.getElementById('debugInfo');
    if (el) { el.insertAdjacentHTML('beforeend', msg.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '<br>'); el.parentElement.classList.remove('hidden'); }
    console.log(msg);
  };

  let tid = null;

  const params = new URLSearchParams(window.location.search);
  const urlTid = params.get('telegram_id');
  if (urlTid) {
    tid = urlTid;
    dbg('TID from URL param: ' + tid);
  } else if (tg) {
    try {
      dbg('=== tg dump ===');
      dbg('tg type: ' + typeof tg);
      dbg('tg constructor: ' + (tg.constructor ? tg.constructor.name : 'none'));
      const keys = Object.getOwnPropertyNames(tg).concat(Object.keys(tg));
      dbg('tg all keys: ' + [...new Set(keys)].join(', '));

      const iu = tg.initDataUnsafe;
      dbg('initDataUnsafe exists: ' + !!iu);
      if (iu) {
        dbg('initDataUnsafe keys: ' + Object.keys(iu).join(', '));
        dbg('initDataUnsafe json: ' + JSON.stringify(iu));
        if (iu.user) {
          tid = String(iu.user.id);
          dbg('*** TID from WebApp user: ' + tid + ' ***');
        } else {
          dbg('initDataUnsafe.user is: ' + typeof iu.user + ' / ' + JSON.stringify(iu.user));
        }
      }
      dbg('initData exists: ' + !!tg.initData);
      if (tg.initData) dbg('initData (first 300): ' + tg.initData.slice(0, 300));

      const h = window.location.hash;
      dbg('location.hash: ' + (h || '(empty)'));
      dbg('location.search: ' + (window.location.search || '(empty)'));
      dbg('=== end tg dump ===');
    } catch(e) {
      dbg('Error reading tg: ' + e.message);
    }
  } else {
    dbg('tg object not available');
    dbg('window.Telegram: ' + typeof window.Telegram);
    dbg('window.Telegram?.WebApp: ' + typeof (window.Telegram && window.Telegram.WebApp));
  }

  async function checkAndShow(idToCheck) {
    try {
      dbg('Fetching /api/me for: ' + idToCheck);
      const res = await fetch('/api/me?telegram_id=' + encodeURIComponent(idToCheck));
      const me = await res.json();
      dbg('API /me: ' + JSON.stringify(me));
      if (!me.exists) { dbg('User not found'); show('registerView'); return; }
      if (me.role === 'admin') {
        dbg('Admin user – showing dashboard');
        document.getElementById('adminName').textContent = me.name + ' ' + me.surname;
        show('adminView');
        const sRes = await fetch('/api/admin/stats?telegram_id=' + encodeURIComponent(idToCheck));
        const stats = await sRes.json();
        if (stats.ok) {
          document.getElementById('statUsers').textContent = stats.total_users;
          document.getElementById('statInterns').textContent = stats.interns;
          document.getElementById('statInstructors').textContent = stats.instructors;
          document.getElementById('statTasks').textContent = stats.tasks;
          dbg('Stats loaded: ' + JSON.stringify(stats));
        }
      } else {
        dbg('Non-admin user – showing welcome');
        document.getElementById('welcomeName').textContent = 'Welcome back, ' + me.name + '!';
        show('welcomeView');
      }
    } catch(e) {
      dbg('Error: ' + e.message);
      show('registerView');
    }
  }

  (async () => {
    if (tid) { await checkAndShow(tid); return; }
    dbg('No TID available – showing registration form');
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

    return {"ok": True, "total_users": total_users, "interns": interns, "instructors": instructors, "tasks": tasks}


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
