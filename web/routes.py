from fastapi import APIRouter

router = APIRouter()


REGISTER_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://telegram.org/js/telegram-webapp.js"></script>
  <title>Create Account</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--tg-theme-bg-color, #fff);
      color: var(--tg-theme-text-color, #000);
      padding: 16px;
    }
    h2 { margin-bottom: 16px; font-size: 20px; }
    form { display: flex; flex-direction: column; gap: 12px; }
    label { font-size: 13px; font-weight: 500; }
    input, select {
      width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #ccc;
      font-size: 15px; background: var(--tg-theme-secondary-bg-color, #f5f5f5);
    }
    button {
      width: 100%; padding: 12px; border: none; border-radius: 8px;
      background: var(--tg-theme-button-color, #40a7e3);
      color: var(--tg-theme-button-text-color, #fff);
      font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 8px;
    }
    .error { color: #e74c3c; font-size: 13px; display: none; }
  </style>
</head>
<body>
  <h2>Create Account</h2>
  <form id="registerForm">
    <label>Name <input name="name" required></label>
    <label>Surname <input name="surname" required></label>
    <label>Phone (+237...) <input name="phone" placeholder="+237XXXXXXXXX" required></label>
    <label>Gender
      <select name="gender" required>
        <option value="">--</option>
        <option value="male">Male</option>
        <option value="female">Female</option>
      </select>
    </label>
    <label>Department
      <select name="department" required>
        <option value="">--</option>
        <option value="ISM">ISM</option>
        <option value="SWE">SWE</option>
        <option value="CGWD">CGWD</option>
        <option value="EDM">EDM</option>
        <option value="CNWS">CNWS</option>
        <option value="NS">NS</option>
      </select>
    </label>
    <label>Group
      <select name="group">
        <option value="">None</option>
        <option value="A">A</option>
        <option value="B">B</option>
      </select>
    </label>
    <label>School <input name="school" required></label>
    <label>Date of Birth <input name="dob" type="date" required></label>

    <p class="error" id="errorMsg"></p>
    <button type="submit">Register</button>
  </form>
  <script>
    const tg = window.Telegram.WebApp;
    tg.ready();

    document.getElementById('registerForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById('errorMsg');
      errorEl.style.display = 'none';

      const form = e.target;
      const data = {
        name: form.name.value,
        surname: form.surname.value,
        phone: form.phone.value,
        telegram_id: String(tg.initDataUnsafe.user.id),
        gender: form.gender.value,
        department: form.department.value,
        group: form.group.value || null,
        school: form.school.value,
        dob: form.dob.value,
      };

      try {
        const res = await fetch('/api/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        const result = await res.json();
        if (res.ok) {
          tg.showAlert('Account created successfully!');
          tg.close();
        } else {
          errorEl.textContent = result.detail || 'Registration failed';
          errorEl.style.display = 'block';
        }
      } catch (err) {
        errorEl.textContent = 'Network error. Please try again.';
        errorEl.style.display = 'block';
      }
    });
  </script>
</body>
</html>"""


@router.get("/app")
async def mini_app():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(REGISTER_HTML)


@router.post("/api/register")
async def register(data: dict):
    from datetime import datetime

    from sqlalchemy import select

    from db.database import async_session
    from models.models import (
        Department,
        Gender,
        Group,
        Role,
        User,
    )

    try:
        async with async_session() as session:
            async with session.begin():
                existing = await session.execute(
                    select(User).where(User.telegram_id == data["telegram_id"])
                )
                if existing.scalar_one_or_none():
                    return {"ok": False, "detail": "User already registered"}

                user = User(
                    name=data["name"],
                    surname=data["surname"],
                    phone=data["phone"],
                    telegram_id=data["telegram_id"],
                    gender=Gender(data["gender"]),
                    role=Role.intern,
                    department=Department(data["department"]),
                    group=Group(data["group"]) if data.get("group") else None,
                    school=data["school"],
                    dob=datetime.strptime(data["dob"], "%Y-%m-%d").date(),
                )
                session.add(user)

        return {"ok": True}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
