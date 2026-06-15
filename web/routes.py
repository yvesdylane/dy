from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse

from web.security import verified_tid

router = APIRouter()

APP_HTML_PATH = Path(__file__).parent / "app.html"
SECTIONS_DIR = Path(__file__).parent / "sections"
REGISTER_HTML_PATH = Path(__file__).parent / "register-standalone.html"
MARK_HTML_PATH = Path(__file__).parent / "mark.html"


def _get_app_html():
    shell = APP_HTML_PATH.read_text()
    for name in ("register","stats","users","codes","attendance","tasks","notes","info"):
        fragment = (SECTIONS_DIR / f"{name}.html").read_text()
        shell = shell.replace(f"<!--SECTION:{name}-->", fragment)
    return shell


HUB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script async src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    body{margin:0;padding:0;background:#09090b;display:flex;align-items:center;justify-content:center;min-height:100dvh}
    .spinner{width:24px;height:24px;border:3px solid #f59e0b;border-top-color:transparent;border-radius:50%;animation:spin .5s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
  </style>
</head>
<body>
  <div class="spinner"></div>
  <script>
  (async function(){
    try{
      var tg=window.Telegram?.WebApp;
      if(tg) tg.ready();
      console.log('hub: tg=',!!tg,'user=',tg?.initDataUnsafe?.user);

      var sp=new URLSearchParams(window.location.search).get('tgWebAppStartParam');
      if(sp&&sp.length>1&&sp[0]==='M'){
        var c=sp.slice(1).replace(/-/g,'+').replace(/_/g,'/');
        var decoded=atob(c);var sep=decoded.indexOf('|');
        if(sep>0){
          window.location.href='/app/mark?d='+encodeURIComponent(decoded.slice(0,sep))+'&s='+encodeURIComponent(decoded.slice(sep+1));
          return;
        }
      }

      var tid=null;
      // attempt 1: tg.initDataUnsafe.user.id
      if(tg&&tg.initDataUnsafe&&tg.initDataUnsafe.user) tid=String(tg.initDataUnsafe.user.id);
      console.log('hub: attempt1 tid=',tid);
      // attempt 2: parse tg.initData directly
      if(!tid&&tg&&tg.initData){
        try{
          var parts=tg.initData.split('&');
          for(var i=0;i<parts.length;i++){
            var kv=parts[i].split('=');
            if(kv[0]==='user'){var u=JSON.parse(decodeURIComponent(kv[1]));tid=String(u.id);break;}
          }
        }catch(e){console.log('hub: parse initData failed',e);}
        console.log('hub: attempt2 tid=',tid);
      }
      // attempt 3: URL hash fallback
      if(!tid){
        try{
          var h=new URLSearchParams((window.location.hash||'').replace(/^#/,''));
          var raw=h.get('tgWebAppData');
          if(raw){
            var p2=raw.split('&');
            for(var j=0;j<p2.length;j++){
              var kv2=p2[j].split('=');
              if(kv2[0]==='user'){var u2=JSON.parse(decodeURIComponent(kv2[1]));tid=String(u2.id);break;}
            }
          }
        }catch(e){console.log('hub: hash parse failed',e);}
        console.log('hub: attempt3 tid=',tid);
      }
      // attempt 4: URL query param
      if(!tid) tid=new URLSearchParams(window.location.search).get('telegram_id');
      console.log('hub: attempt4 tid=',tid);
      console.log('hub: final tid=',tid);

      if(!tid){console.log('hub: no tid → register');window.location.href='/app/register';return;}
      console.log('hub: fetching /api/me');
      var resp=await fetch('/api/me?telegram_id='+encodeURIComponent(tid));
      console.log('hub: /api/me status',resp.status);
      var me=await resp.json();
      console.log('hub: /api/me body',JSON.stringify(me));
      if(!me.exists){console.log('hub: user not found → register');window.location.href='/app/register?telegram_id='+encodeURIComponent(tid);}
      else if(me.role==='admin'){console.log('hub: admin → dashboard');window.location.href='/app/admin?telegram_id='+encodeURIComponent(tid);}
      else{
        console.log('hub: non-admin role',me.role,'→ close');
        document.body.innerHTML='<p style="color:#a1a1aa;font-family:sans-serif;text-align:center;padding:40px 20px;font-size:14px">No dashboard available for your role yet.</p>';
        setTimeout(function(){if(tg) tg.close();},3000);
      }
    }catch(e){console.error('hub: error',e);window.location.href='/app/register';}
  })();
  </script>
</body>
</html>"""


@router.get("/app")
async def app_hub():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(HUB_HTML)


@router.get("/app/admin")
async def admin_dashboard():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(_get_app_html())


@router.get("/app/register")
async def register_page():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(REGISTER_HTML_PATH.read_text())


@router.get("/app/mark")
async def mark_page():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(MARK_HTML_PATH.read_text())


@router.get("/s")
async def launch_redirect():
    return RedirectResponse(url="/app")


@router.get("/mark")
async def mark_redirect():
    return RedirectResponse(url="/app/mark")

@router.get("/api/me")
async def get_me(telegram_id: str = Depends(verified_tid)):
    import logging

    from sqlalchemy import select

    from db.database import async_session
    from models.models import User

    logger = logging.getLogger("api.me")
    logger.info("=== /api/me CALLED — telegram_id=%s ===", telegram_id)

    async with async_session() as session:
        logger.info("=== /api/me — before query ===")
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        logger.info("=== /api/me — after query ===")
        user = result.scalar_one_or_none()

    if not user:
        logger.info("=== /api/me — user not found, returning ===")
        return {"exists": False}
    logger.info("=== /api/me — found user: %s %s, role: %s, returning ===", user.name, user.surname, user.role.value)
    return {
        "exists": True,
        "id": user.id,
        "name": user.name,
        "surname": user.surname,
        "role": user.role.value,
    }


@router.get("/api/admin/stats")
async def admin_stats(telegram_id: str = Depends(verified_tid)):
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
        total_fees = (await session.execute(
            select(func.sum(User.total_fees)).where(User.role == Role.intern)
        )).scalar() or 0
        total_paid = (await session.execute(
            select(func.sum(User.fees_paid)).where(User.role == Role.intern)
        )).scalar() or 0

    total_fees = float(total_fees)
    total_paid = float(total_paid)
    return {"ok": True, "total_users": total_users, "interns": interns,
        "instructors": instructors, "tasks": tasks,
        "total_fees": total_fees, "total_paid": total_paid, "outstanding": total_fees - total_paid}


@router.get("/api/admin/users")
async def admin_list_users(telegram_id: str = Depends(verified_tid)):
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
async def admin_create_user(telegram_id: str = Depends(verified_tid), data: dict = None):
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
async def admin_update_user(user_id: int, telegram_id: str = Depends(verified_tid), data: dict = None):
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
async def admin_delete_user(user_id: int, telegram_id: str = Depends(verified_tid)):
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
async def admin_list_codes(telegram_id: str = Depends(verified_tid)):
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
async def admin_create_code(telegram_id: str = Depends(verified_tid), data: dict = None):
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
async def admin_delete_code(code_id: int, telegram_id: str = Depends(verified_tid)):
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
    from models.models import CreationCode, Department, Gender, Group, Role, User

    try:
        async with async_session() as session:
            async with session.begin():
                existing = await session.execute(
                    select(User).where(User.telegram_id == data["telegram_id"])
                )
                if existing.scalar_one_or_none():
                    return {"ok": False, "detail": "User already registered"}

                code_val = data.get("code", "")
                if not code_val:
                    return {"ok": False, "detail": "Registration code is required"}
                cc = await session.execute(
                    select(CreationCode).where(
                        CreationCode.code == code_val,
                        CreationCode.is_used == False,
                        CreationCode.expires_at > datetime.utcnow()
                    )
                )
                cc = cc.scalar_one_or_none()
                if not cc:
                    return {"ok": False, "detail": "Invalid or expired registration code"}
                role = cc.role
                cc.is_used = True

                session.add(User(
                    name=data["name"], surname=data["surname"], phone=data["phone"],
                    telegram_id=data["telegram_id"], gender=Gender(data["gender"]),
                    role=role, department=Department(data["department"]),
                    group=Group(data["group"]) if data.get("group") else None,
                    school=data["school"],
                    dob=datetime.strptime(data["dob"], "%Y-%m-%d").date(),
                ))

        return {"ok": True}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


MARK_QR_MAX_AGE = 3600


@router.get("/api/mark")
async def mark_attendance(
    telegram_id: str = Depends(verified_tid),
    d: str = Query(...),
    s: str = Query(...),
):
    from datetime import date, datetime

    from sqlalchemy import select

    from config import settings
    from db.database import async_session
    from models.models import Attendance, Group, InternAttendance, User
    from web.security import verify_qr_payload

    qr_data = verify_qr_payload(d, s, settings.telegram_token, MARK_QR_MAX_AGE)
    if not qr_data:
        return {"ok": False, "message": "Invalid or expired QR code"}

    if qr_data.get("date") != str(date.today()):
        return {"ok": False, "message": "QR code is for a different date"}

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user.scalar_one_or_none()

            if not user:
                return {
                    "ok": False,
                    "needs_register": True,
                    "telegram_id": telegram_id,
                    "message": "Create an account first",
                }

            weekday = date.today().weekday()
            if weekday == 6:
                return {"ok": False, "message": "No attendance on Sundays"}

            today_group = Group.A if weekday in (0, 2, 4) else Group.B

            if user.group != today_group:
                return {
                    "ok": False,
                    "message": f"Today is Group {today_group.value}, you are Group {user.group.value}",
                }

            att = await session.execute(
                select(Attendance).where(
                    Attendance.date == date.today(),
                    Attendance.group == today_group,
                )
            )
            att = att.scalar_one_or_none()
            if not att:
                att = Attendance(date=date.today(), group=today_group)
                session.add(att)
                await session.flush()

            entry = await session.execute(
                select(InternAttendance).where(
                    InternAttendance.attendance_id == att.id,
                    InternAttendance.user_id == user.id,
                )
            )
            entry = entry.scalar_one_or_none()

            now = datetime.utcnow()
            if not entry:
                entry = InternAttendance(
                    attendance_id=att.id,
                    user_id=user.id,
                    enter_at=now,
                )
                session.add(entry)
                msg = f"✅ Entry marked at {now.strftime('%H:%M')}"
            else:
                entry.left_at = now
                msg = f"✅ Exit marked at {now.strftime('%H:%M')}"

    return {"ok": True, "message": msg}
