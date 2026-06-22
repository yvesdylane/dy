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
    for name in ("register","stats","people","attendance","tasks","notes","bulletin"):
        fragment = (SECTIONS_DIR / f"{name}.html").read_text()
        shell = shell.replace(f"<!--SECTION:{name}-->", fragment)
    # Second pass — resolve nested section placeholders inside wrapper fragments
    for name in ("users","codes","info","registers","leaves","cleaning"):
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


@router.post("/api/admin/save-db")
async def admin_save_db(telegram_id: str = Depends(verified_tid)):
    from io import BytesIO

    from sqlalchemy import select

    from bot.router import application
    from db.database import async_session
    from models.models import Role, User

    async with async_session() as session:
        admin = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

    if not application:
        return {"ok": False, "detail": "Bot not initialized"}

    db_path = Path("dy.db")
    if not db_path.exists():
        return {"ok": False, "detail": "Database file not found"}

    try:
        data = db_path.read_bytes()
        buf = BytesIO(data)
        buf.name = "dy.db"
        await application.bot.send_document(
            chat_id=telegram_id,
            document=buf,
            caption=f"📦 dy.db backup — {len(data)} bytes",
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


@router.get("/api/admin/users")
async def admin_list_users(
    telegram_id: str = Depends(verified_tid),
    group: str = Query(None), page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    from sqlalchemy import func, select

    from db.database import async_session
    from models.models import Group, Role, User

    async with async_session() as session:
        admin = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        q = select(User)
        if group:
            try:
                g = Group(group)
            except ValueError:
                return {"ok": False, "detail": "Invalid group"}
            q = q.where(User.group == g)

        count_q = select(func.count(User.id))
        if group:
            count_q = count_q.where(User.group == g)
        total = (await session.execute(count_q)).scalar()

        q = q.order_by(User.id).offset((page - 1) * per_page).limit(per_page)
        users = (await session.execute(q)).scalars().all()

    return {"ok": True, "total": total, "page": page, "per_page": per_page, "users": [{
        "id": u.id, "name": u.name, "surname": u.surname, "phone": u.phone,
        "telegram_id": u.telegram_id, "gender": u.gender.value,
        "role": u.role.value, "department": u.department.value,
        "group": u.group.value if u.group else None,
        "school": u.school, "dob": str(u.dob),
        "linked": not u.telegram_id.startswith("pending_"),
        "fees_paid": float(u.fees_paid) if u.fees_paid else 0,
        "total_fees": float(u.total_fees) if u.total_fees else 0,
        "image": u.image,
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
            if "telegram_id" in data:
                dup = await session.execute(
                    select(User).where(User.telegram_id == data["telegram_id"], User.id != user_id)
                )
                if dup.scalar_one_or_none():
                    return {"ok": False, "detail": "Telegram ID already in use"}
                user.telegram_id = data["telegram_id"]

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

            role_val = data.get("role", "intern") if data else "intern"
            expiry_minutes = data.get("expiry_minutes", 60) if data else 60
            count = min(data.get("count", 1) if data else 1, 100)

            codes = []
            for _ in range(count):
                code = str(random.randint(100000, 999999))
                while True:
                    exists = await session.execute(
                        select(CreationCode).where(CreationCode.code == code)
                    )
                    if not exists.scalar_one_or_none():
                        break
                    code = str(random.randint(100000, 999999))

                cc = CreationCode(
                    code=code, role=Role(role_val),
                    expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes),
                    created_by=admin_user.id,
                )
                session.add(cc)
                codes.append({"id": cc.id, "code": cc.code, "role": cc.role.value})

    return {"ok": True, "codes": codes}


@router.post("/api/admin/codes/delete-batch")
async def admin_delete_codes_batch(telegram_id: str = Depends(verified_tid), data: dict = None):
    from sqlalchemy import select, text
    from db.database import async_session
    from models.models import CreationCode, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            if data and data.get("all"):
                await session.execute(text("DELETE FROM creation_codes"))
            elif data and data.get("ids"):
                for cc_id in data["ids"]:
                    cc = await session.get(CreationCode, cc_id)
                    if cc:
                        await session.delete(cc)
            else:
                return {"ok": False, "detail": "Provide ids or all=true"}

    return {"ok": True}


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
                existing_tid = await session.execute(
                    select(User).where(User.telegram_id == data["telegram_id"])
                )
                if existing_tid.scalar_one_or_none():
                    return {"ok": False, "detail": "User already registered"}

                phone = data["phone"]
                if not phone.startswith("+"):
                    phone = "+237" + phone

                existing_phone = await session.execute(
                    select(User).where(User.phone == phone)
                )
                existing_user = existing_phone.scalar_one_or_none()
                if existing_user:
                    existing_user.telegram_id = data["telegram_id"]
                    return {"ok": True, "role": existing_user.role.value, "linked": True}

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
                    name=data["name"], surname=data["surname"], phone=phone,
                    telegram_id=data["telegram_id"], gender=Gender(data["gender"]),
                    role=role, department=Department(data["department"]),
                    group=Group(data["group"]) if data.get("group") else None,
                    school=data["school"],
                    dob=datetime.strptime(data["dob"], "%Y-%m-%d").date(),
                ))

        return {"ok": True, "role": role.value}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


@router.get("/api/admin/complaints")
async def admin_list_complaints(telegram_id: str = Depends(verified_tid), format: str = None):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Role, User, UserComplain

    async with async_session() as session:
        admin = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        items = (await session.execute(
            select(UserComplain).order_by(UserComplain.created_at.desc()).limit(200)
        )).scalars().all()

    if format == "csv":
        import csv
        import io
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["Type", "Department", "Group", "Content", "Date"])
        for item in items:
            w.writerow([
                item.complain_type.value,
                item.department.value,
                item.group.value if item.group else "",
                item.content,
                item.created_at.strftime("%Y-%m-%d %H:%M"),
            ])
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=complaints.csv"})

    return {"ok": True, "complaints": [{
        "id": item.id,
        "content": item.content,
        "type": item.complain_type.value,
        "department": item.department.value,
        "group": item.group.value if item.group else None,
        "created_at": item.created_at.strftime("%Y-%m-%d %H:%M"),
    } for item in items]}


# ── Cleaning Roster ─────────────────────────────────────────────


@router.get("/api/admin/cleaning/groups")
async def admin_list_cleaning_groups(telegram_id: str = Depends(verified_tid)):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from db.database import async_session
    from models.models import CleaningGroup, CleaningGroupMember, Role, User

    async with async_session() as session:
        admin = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        groups = (await session.execute(
            select(CleaningGroup)
            .options(selectinload(CleaningGroup.members).selectinload(CleaningGroupMember.user))
            .order_by(CleaningGroup.turn_order)
        )).scalars().all()

    result = []
    all_cleaned = []
    for g in groups:
        pending = []
        cleaned = []
        for m in g.members:
            u = m.user
            entry = {
                "id": m.id,
                "user_id": u.id,
                "name": u.name,
                "surname": u.surname,
                "gender": u.gender.value,
                "cycle_cleaned": m.cycle_cleaned,
            }
            if m.cycle_cleaned:
                cleaned.append(entry)
            else:
                pending.append(entry)
        result.append({
            "id": g.id,
            "name": g.name,
            "department": g.department.value,
            "turn_order": g.turn_order,
            "members": pending,
        })
        all_cleaned.extend(cleaned)

    return {"ok": True, "groups": result, "cleaned_members": all_cleaned}


@router.get("/api/admin/cleaning/status")
async def admin_cleaning_status(telegram_id: str = Depends(verified_tid)):
    from datetime import date

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from db.database import async_session
    from models.models import CleaningDuty, CleaningGroup, CleaningGroupMember, Role, User

    async with async_session() as session:
        admin_user = (await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )).scalar_one_or_none()
        if not admin_user:
            return {"ok": False, "detail": "Unauthorized"}

        groups_count = (await session.execute(
            select(CleaningGroup).where(CleaningGroup.department == admin_user.department)
        )).scalars().all()

        has_groups = len(groups_count) > 0

        today = date.today()
        duty = (await session.execute(
            select(CleaningDuty)
            .options(
                selectinload(CleaningDuty.group).selectinload(CleaningGroup.members).selectinload(CleaningGroupMember.user),
                selectinload(CleaningDuty.completions),
            )
            .where(CleaningDuty.date == today)
        )).scalar_one_or_none()

        # Check cycle progress
        all_members = (await session.execute(
            select(CleaningGroupMember)
        )).scalars().all()
        total_members = len(all_members)
        cleaned_count = sum(1 for m in all_members if m.cycle_cleaned)
        cycle_done = total_members > 0 and cleaned_count >= total_members

    today_duty = None
    if duty:
        members_list = []
        for m in duty.group.members:
            completed = any(c.user_id == m.user_id for c in duty.completions)
            members_list.append({
                "id": m.id,
                "user_id": m.user_id,
                "name": m.user.name,
                "surname": m.user.surname,
                "completed": completed,
            })
        today_duty = {
            "id": duty.id,
            "group_id": duty.group.id,
            "group_name": duty.group.name,
            "date": duty.date.isoformat(),
            "status": duty.status,
            "members": members_list,
        }

    return {
        "ok": True,
        "has_groups": has_groups,
        "today_duty": today_duty,
        "cycle_progress": {"total": total_members, "cleaned": cleaned_count, "done": cycle_done},
    }


@router.post("/api/admin/cleaning/start")
async def admin_start_cleaning(telegram_id: str = Depends(verified_tid), data: dict = None):
    from datetime import date

    from sqlalchemy import select

    from db.database import async_session
    from models.models import (
        CleaningGroup, CleaningGroupMember, Department, Gender, Role, User,
    )

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            admin = admin.scalar_one_or_none()
            if not admin:
                return {"ok": False, "detail": "Unauthorized"}

            dept = Department.SWE
            already_cleaned_ids = set(data.get("already_cleaned_ids", []))

            interns = (await session.execute(
                select(User).where(User.role == Role.intern, User.department == dept)
            )).scalars().all()

            if len(interns) < 2:
                return {"ok": False, "detail": "Not enough interns for cleaning groups"}

            males = [u for u in interns if u.gender == Gender.male]
            females = [u for u in interns if u.gender == Gender.female]
            import random
            random.shuffle(males)
            random.shuffle(females)

            group_size = max(3, min(5, (len(interns) + 2) // 3))
            groups = []
            while males or females:
                group = []
                if males and (len(groups) < len(males) or not females):
                    group.append(males.pop())
                while len(group) < group_size and females:
                    group.append(females.pop())
                while len(group) < group_size and males:
                    group.append(males.pop())
                if group:
                    groups.append(group)

            existing = (await session.execute(
                select(CleaningGroup)
            )).scalars().all()
            for g in existing:
                await session.delete(g)

            for i, members in enumerate(groups):
                cg = CleaningGroup(
                    name=f"Cleaning Group {chr(65 + i)}",
                    department=dept,
                    turn_order=i,
                )
                session.add(cg)
                await session.flush()
                for u in members:
                    session.add(CleaningGroupMember(
                        group_id=cg.id,
                        user_id=u.id,
                        cycle_cleaned=u.id in already_cleaned_ids,
                    ))

    return {"ok": True}


@router.post("/api/admin/cleaning/members/{member_id}/toggle-cycle")
async def admin_toggle_cycle_cleaned(member_id: int, telegram_id: str = Depends(verified_tid)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import CleaningGroupMember, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            member = await session.get(CleaningGroupMember, member_id)
            if not member:
                return {"ok": False, "detail": "Member not found"}
            member.cycle_cleaned = not member.cycle_cleaned

    return {"ok": True, "cycle_cleaned": member.cycle_cleaned}


@router.post("/api/admin/cleaning/cleaned-members")
async def admin_add_cleaned_members(telegram_id: str = Depends(verified_tid), data: dict = None):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import CleaningGroup, CleaningGroupMember, Role, User

    user_ids = data.get("user_ids", [])
    if not user_ids:
        return {"ok": False, "detail": "user_ids required"}

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            first_group = (await session.execute(
                select(CleaningGroup).order_by(CleaningGroup.turn_order).limit(1)
            )).scalar_one_or_none()
            if not first_group:
                return {"ok": False, "detail": "No cleaning groups exist"}

            for uid in user_ids:
                member = (await session.execute(
                    select(CleaningGroupMember).where(CleaningGroupMember.user_id == uid)
                )).scalar_one_or_none()
                if member:
                    member.cycle_cleaned = True
                else:
                    session.add(CleaningGroupMember(
                        group_id=first_group.id,
                        user_id=uid,
                        cycle_cleaned=True,
                    ))

    return {"ok": True}
async def admin_add_cleaning_members(group_id: int, telegram_id: str = Depends(verified_tid), data: dict = None):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import CleaningGroup, CleaningGroupMember, Role, User

    user_ids = data.get("user_ids", [])
    if not user_ids:
        return {"ok": False, "detail": "user_ids required"}

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            group = await session.get(CleaningGroup, group_id)
            if not group:
                return {"ok": False, "detail": "Group not found"}

            for uid in user_ids:
                existing = (await session.execute(
                    select(CleaningGroupMember).where(CleaningGroupMember.user_id == uid)
                )).scalar_one_or_none()
                if existing:
                    existing.group_id = group_id
                    existing.cycle_cleaned = False
                else:
                    session.add(CleaningGroupMember(group_id=group_id, user_id=uid))

    return {"ok": True}


@router.delete("/api/admin/cleaning/members/{member_id}")
async def admin_remove_cleaning_member(member_id: int, telegram_id: str = Depends(verified_tid)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import CleaningGroupMember, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            member = await session.get(CleaningGroupMember, member_id)
            if not member:
                return {"ok": False, "detail": "Member not found"}
            await session.delete(member)

    return {"ok": True}


@router.put("/api/admin/cleaning/members/{member_id}/move")
async def admin_move_cleaning_member(member_id: int, telegram_id: str = Depends(verified_tid), data: dict = None):
    from db.database import async_session
    from models.models import CleaningGroup, CleaningGroupMember, Role, User

    new_group_id = data.get("group_id")
    if not new_group_id:
        return {"ok": False, "detail": "group_id required"}

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            member = await session.get(CleaningGroupMember, member_id)
            if not member:
                return {"ok": False, "detail": "Member not found"}

            group = await session.get(CleaningGroup, new_group_id)
            if not group:
                return {"ok": False, "detail": "Target group not found"}

            member.group_id = new_group_id

    return {"ok": True}
async def admin_list_cleaning_duties(telegram_id: str = Depends(verified_tid), limit: int = 14):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from db.database import async_session
    from models.models import CleaningDuty, Role, User

    async with async_session() as session:
        admin = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        duties = (await session.execute(
            select(CleaningDuty)
            .options(
                selectinload(CleaningDuty.group),
                selectinload(CleaningDuty.completions),
            )
            .order_by(CleaningDuty.date.desc())
            .limit(limit)
        )).scalars().all()

    return {"ok": True, "duties": [{
        "id": d.id,
        "group_name": d.group.name,
        "date": d.date.isoformat(),
        "status": d.status,
        "completed_count": sum(1 for c in d.completions),
    } for d in duties]}


@router.post("/api/admin/cleaning/duties/{duty_id}/complete")
async def admin_complete_cleaning(duty_id: int, telegram_id: str = Depends(verified_tid), data: dict = None):
    from datetime import datetime

    from sqlalchemy import select

    from db.database import async_session
    from models.models import CleaningCompletion, CleaningDuty, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            duty = await session.get(CleaningDuty, duty_id)
            if not duty:
                return {"ok": False, "detail": "Duty not found"}

            user_id = data.get("user_id")
            if not user_id:
                return {"ok": False, "detail": "user_id required"}

            existing = (await session.execute(
                select(CleaningCompletion).where(
                    CleaningCompletion.duty_id == duty_id,
                    CleaningCompletion.user_id == user_id,
                )
            )).scalar_one_or_none()

            if existing:
                return {"ok": False, "detail": "Already marked complete"}

            session.add(CleaningCompletion(
                duty_id=duty_id,
                user_id=user_id,
            ))

            # Update member's cycle_cleaned flag
            from models.models import CleaningGroupMember
            member = (await session.execute(
                select(CleaningGroupMember).where(
                    CleaningGroupMember.group_id == duty.group_id,
                    CleaningGroupMember.user_id == user_id,
                )
            )).scalar_one_or_none()
            if member:
                member.cycle_cleaned = True

            # If all completions match group member count, mark duty complete
            members_count = (await session.execute(
                select(CleaningGroupMember).where(CleaningGroupMember.group_id == duty.group_id)
            )).scalars().all()
            completions_count = (await session.execute(
                select(CleaningCompletion).where(CleaningCompletion.duty_id == duty_id)
            )).scalars().all()
            if len(completions_count) >= len(members_count):
                duty.status = "completed"
                duty.completed_at = datetime.utcnow()

    return {"ok": True, "completed": True}


@router.post("/api/admin/cleaning/reset-cycles")
async def admin_reset_cleaning_cycles(telegram_id: str = Depends(verified_tid)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import CleaningGroupMember, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            members = (await session.execute(
                select(CleaningGroupMember)
            )).scalars().all()
            for m in members:
                m.cycle_cleaned = False

    return {"ok": True}


@router.get("/api/admin/cleaning/interns")
async def admin_cleaning_interns(telegram_id: str = Depends(verified_tid)):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import Department, Role, User

    async with async_session() as session:
        admin = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        interns = (await session.execute(
            select(User).where(User.role == Role.intern, User.department == Department.SWE)
            .order_by(User.name)
        )).scalars().all()

    return {"ok": True, "interns": [{
        "id": u.id,
        "name": u.name,
        "surname": u.surname,
        "gender": u.gender.value,
    } for u in interns]}


@router.post("/api/leave")
async def submit_leave(telegram_id: str = Depends(verified_tid), data: dict = None):
    from datetime import date

    from sqlalchemy import select

    from db.database import async_session
    from models.models import LeaveRequest, User

    async with async_session() as session:
        async with session.begin():
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user.scalar_one_or_none()
            if not user:
                return {"ok": False, "detail": "User not found"}

            leave_date = date.fromisoformat(data["date"])
            session.add(LeaveRequest(
                user_id=user.id,
                date=leave_date,
                reason=data["reason"],
            ))

    return {"ok": True}


@router.get("/api/admin/leaves")
async def admin_list_leaves(telegram_id: str = Depends(verified_tid)):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from db.database import async_session
    from models.models import LeaveRequest, Role, User

    async with async_session() as session:
        admin = await session.execute(
            select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
        )
        if not admin.scalar_one_or_none():
            return {"ok": False, "detail": "Unauthorized"}

        items = (await session.execute(
            select(LeaveRequest)
            .options(selectinload(LeaveRequest.user))
            .order_by(LeaveRequest.created_at.desc()).limit(200)
        )).scalars().all()

        result = []
        for lr in items:
            u = lr.user
            result.append({
                "id": lr.id,
                "user_id": lr.user_id,
                "user_name": f"{u.name} {u.surname}",
                "department": u.department.value,
                "group": u.group.value if u.group else None,
                "date": lr.date.isoformat(),
                "reason": lr.reason,
                "status": lr.status.value,
                "created_at": lr.created_at.strftime("%Y-%m-%d %H:%M"),
            })

    return {"ok": True, "leaves": result}


@router.post("/api/admin/leaves/{leave_id}/review")
async def admin_review_leave(leave_id: int, telegram_id: str = Depends(verified_tid), data: dict = None):
    from sqlalchemy import select

    from db.database import async_session
    from models.models import InternAttendance, LeaveRequest, LeaveStatus, Role, User

    async with async_session() as session:
        async with session.begin():
            admin = await session.execute(
                select(User).where(User.telegram_id == telegram_id, User.role == Role.admin)
            )
            if not admin.scalar_one_or_none():
                return {"ok": False, "detail": "Unauthorized"}

            lr = await session.get(LeaveRequest, leave_id)
            if not lr:
                return {"ok": False, "detail": "Leave request not found"}

            new_status = data.get("status")
            if new_status not in ("approved", "rejected"):
                return {"ok": False, "detail": "Invalid status"}

            lr.status = LeaveStatus(new_status)
            lr.reviewed_by = admin.scalar_one().id

            if new_status == "approved":
                from datetime import datetime
                from models.models import Attendance
                att = await session.execute(
                    select(Attendance).where(Attendance.date == lr.date)
                )
                att = att.scalar_one_or_none()
                if att:
                    existing = await session.execute(
                        select(InternAttendance).where(
                            InternAttendance.attendance_id == att.id,
                            InternAttendance.user_id == lr.user_id,
                        )
                    )
                    ia = existing.scalar_one_or_none()
                    if not ia:
                        ia = InternAttendance(
                            attendance_id=att.id,
                            user_id=lr.user_id,
                            enter_at=datetime.combine(lr.date, datetime.min.time()),
                            status="exempted",
                        )
                        session.add(ia)
                    else:
                        ia.status = "exempted"

    return {"ok": True}


@router.get("/api/files/{file_id}")
async def serve_file(file_id: str):
    from bot.router import application

    if not application:
        return {"ok": False, "detail": "Bot not initialized"}
    try:
        file = await application.bot.get_file(file_id)
        data = await file.download_as_bytearray()
        from fastapi.responses import Response
        return Response(content=data, media_type="application/octet-stream")
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
