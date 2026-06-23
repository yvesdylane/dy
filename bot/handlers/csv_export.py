from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, filters

from bot.handlers.common import get_user

CSV_FILTER_OPTIONS = {
    "role": [("Intern", "intern"), ("Instructor", "instructor"), ("Admin", "admin")],
    "dept": [("ISM", "ISM"), ("SWE", "SWE"), ("CGWD", "CGWD"), ("EDM", "EDM"),
             ("CSNW", "CSNW"), ("DBM", "DBM"), ("CNWS", "CNWS"), ("NS", "NS")],
    "group": [("A", "A"), ("B", "B")],
    "gender": [("Male", "male"), ("Female", "female")],
    "fees": [("Paid in full", "paid"), ("Not paid", "unpaid"),
             ("Remaining > 0", "remaining"), ("Remaining >= 5000", "remaining_5000"),
             ("Remaining < 5000", "remaining_under")],
    "linked": [("Linked", "linked"), ("Pending", "pending")],
}

CSV_FILTER_LABELS = {
    "role": "Role", "dept": "Department", "group": "Group",
    "gender": "Gender", "fees": "Fee Status", "linked": "Linked",
}

ACSV_FILTER_LABELS = {
    "group": "Group",
    "dept": "Department",
    "period": "Period",
}

ACSV_PERIOD_OPTIONS = [
    ("Last 7 days", "7d"),
    ("Last 30 days", "30d"),
    ("All time", "all"),
]


# ── User CSV Export ──────────────────────────────────────────────


async def csv_user_start(update: Update, context):
    from models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.instructor):
        await update.message.reply_text("Only instructors and admins can use this command.")
        return
    context.user_data["csv_filters"] = {}
    await _csv_show_menu(update, context, edit=False)


async def _csv_show_menu(update, context, edit=True):
    filters = context.user_data.get("csv_filters", {})
    text = "*User CSV Export*\nSelect filters below, then generate."
    if filters:
        text += "\n\n*Active filters:*"
        for k, v in filters.items():
            label = CSV_FILTER_LABELS.get(k, k)
            text += f"\n• {label}: `{v}`"

    rows = []
    for key, label in CSV_FILTER_LABELS.items():
        rows.append([InlineKeyboardButton(
            f"{label}: {filters.get(key, 'Any')}",
            callback_data=f"csv:filter:{key}",
        )])
    rows.append([InlineKeyboardButton("📥 Generate CSV", callback_data="csv:generate")])

    msg = update.callback_query.message if edit else update.message
    kwargs = {"parse_mode": "Markdown", "reply_markup": InlineKeyboardMarkup(rows)}
    if edit:
        await msg.edit_text(text, **kwargs)
    else:
        await msg.reply_text(text, **kwargs)


async def csv_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "csv:generate":
        await _csv_generate(update, context)
        return

    if data.startswith("csv:filter:"):
        filter_name = data.split(":", 2)[2]
        options = CSV_FILTER_OPTIONS.get(filter_name, [])
        if not options:
            return
        text = f"Select *{CSV_FILTER_LABELS.get(filter_name, filter_name)}*:"
        keyboard = [
            [InlineKeyboardButton(f"◀ Back", callback_data="csv:menu")],
        ]
        for lbl, val in options:
            keyboard.append([InlineKeyboardButton(lbl, callback_data=f"csv:set:{filter_name}:{val}")])
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("csv:set:"):
        parts = data.split(":", 2)
        rest = parts[2]
        filter_name, filter_val = rest.split(":", 1)
        context.user_data.setdefault("csv_filters", {})[filter_name] = filter_val
        await _csv_show_menu(update, context)

    if data == "csv:menu":
        await _csv_show_menu(update, context)


async def _csv_generate(update, context):
    import csv
    import io

    from uuid import uuid4

    from sqlalchemy import select

    from db.database import async_session
    from models.models import User as UserModel

    query = update.callback_query
    filters = context.user_data.get("csv_filters", {})

    stmt = select(UserModel)
    if "role" in filters:
        from models.models import Role
        stmt = stmt.where(UserModel.role == Role(filters["role"]))
    if "dept" in filters:
        from models.models import Department
        stmt = stmt.where(UserModel.department == Department(filters["dept"]))
    if "group" in filters:
        from models.models import Group
        stmt = stmt.where(UserModel.group == Group(filters["group"]))
    if "gender" in filters:
        from models.models import Gender
        stmt = stmt.where(UserModel.gender == Gender(filters["gender"]))
    if "fees" in filters:
        val = filters["fees"]
        if val == "paid":
            stmt = stmt.where(UserModel.fees_paid >= UserModel.total_fees)
        elif val == "unpaid":
            stmt = stmt.where((UserModel.fees_paid == None) | (UserModel.fees_paid == 0))
        elif val == "remaining":
            stmt = stmt.where(UserModel.total_fees - UserModel.fees_paid > 0)
        elif val == "remaining_5000":
            stmt = stmt.where(UserModel.total_fees - UserModel.fees_paid >= 5000)
        elif val == "remaining_under":
            stmt = stmt.where(
                (UserModel.total_fees - UserModel.fees_paid > 0) &
                (UserModel.total_fees - UserModel.fees_paid < 5000)
            )
    if "linked" in filters:
        if filters["linked"] == "linked":
            stmt = stmt.where(~UserModel.telegram_id.startswith("pending_"))
        else:
            stmt = stmt.where(UserModel.telegram_id.startswith("pending_"))

    await query.message.edit_text("Generating CSV…")

    async with async_session() as session:
        users = (await session.execute(stmt.order_by(UserModel.id))).scalars().all()

    buf = io.StringIO()
    w = csv.writer(buf)
    headers = ["ID", "Name", "Surname", "Phone", "Telegram ID", "Gender", "Role",
               "Department", "Group", "School", "DOB", "Quarter", "Fees Paid",
               "Total Fees", "Linked", "Image"]
    w.writerow(headers)
    for u in users:
        w.writerow([
            u.id, u.name, u.surname, u.phone, u.telegram_id,
            u.gender.value, u.role.value, u.department.value,
            u.group.value if u.group else "", u.school, str(u.dob),
            u.quarter or "", float(u.fees_paid or 0), float(u.total_fees or 0),
            "Yes" if not u.telegram_id.startswith("pending_") else "No",
            u.image or "",
        ])

    csv_bytes = buf.getvalue().encode("utf-8")
    buf_io = io.BytesIO(csv_bytes)
    buf_io.name = f"users_{uuid4().hex[:8]}.csv"
    await query.message.reply_document(document=buf_io, filename=buf_io.name, caption=f"📊 Users: {len(users)} rows")
    del context.user_data["csv_filters"]


# ── Attendance CSV Export ────────────────────────────────────────


async def attend_csv_start(update: Update, context):
    from models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user or user.role not in (Role.admin, Role.instructor):
        await update.message.reply_text("Only instructors and admins can use this command.")
        return
    context.user_data["acsv_filters"] = {}
    await _acsv_show_menu(update, context, edit=False)


async def _acsv_show_menu(update, context, edit=True):
    filters = context.user_data.get("acsv_filters", {})
    text = "*Attendance CSV Export*\nSelect filters, then generate."
    if filters:
        text += "\n\n*Active filters:*"
        for k, v in filters.items():
            label = ACSV_FILTER_LABELS.get(k, k)
            text += f"\n• {label}: `{v}`"

    rows = [
        [InlineKeyboardButton(f"Group: {filters.get('group', 'Any')}", callback_data="acsv:filter:group")],
        [InlineKeyboardButton(f"Department: {filters.get('dept', 'Any')}", callback_data="acsv:filter:dept")],
        [InlineKeyboardButton(f"Period: {filters.get('period', 'All time')}", callback_data="acsv:filter:period")],
        [InlineKeyboardButton("📥 Generate CSV", callback_data="acsv:generate")],
    ]

    msg = update.callback_query.message if edit else update.message
    kwargs = {"parse_mode": "Markdown", "reply_markup": InlineKeyboardMarkup(rows)}
    if edit:
        await msg.edit_text(text, **kwargs)
    else:
        await msg.reply_text(text, **kwargs)


async def acsv_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "acsv:generate":
        await _acsv_generate(update, context)
        return

    if data.startswith("acsv:filter:"):
        filter_name = data.split(":", 2)[2]
        text = f"Select *{ACSV_FILTER_LABELS.get(filter_name, filter_name)}*:"

        if filter_name == "group":
            options = [("A", "A"), ("B", "B")]
        elif filter_name == "dept":
            from models.models import Department
            options = [(d.value, d.value) for d in Department]
        elif filter_name == "period":
            options = ACSV_PERIOD_OPTIONS
        else:
            return

        keyboard = [[InlineKeyboardButton("◀ Back", callback_data="acsv:menu")]]
        for lbl, val in options:
            keyboard.append([InlineKeyboardButton(lbl, callback_data=f"acsv:set:{filter_name}:{val}")])
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("acsv:set:"):
        parts = data.split(":", 2)
        rest = parts[2]
        filter_name, filter_val = rest.split(":", 1)
        context.user_data.setdefault("acsv_filters", {})[filter_name] = filter_val
        await _acsv_show_menu(update, context)

    if data == "acsv:menu":
        await _acsv_show_menu(update, context)


async def _acsv_generate(update, context):
    import csv
    import io
    from datetime import datetime, timedelta
    from uuid import uuid4

    from sqlalchemy import select

    from db.database import async_session
    from models.models import Attendance, InternAttendance, User as UserModel

    query = update.callback_query
    filters = context.user_data.get("acsv_filters", {})

    stmt = (
        select(Attendance.date, Attendance.group, UserModel.name, UserModel.surname,
               UserModel.phone, UserModel.department, InternAttendance.enter_at,
               InternAttendance.left_at)
        .join(InternAttendance, InternAttendance.attendance_id == Attendance.id)
        .join(UserModel, UserModel.id == InternAttendance.user_id)
    )

    if "group" in filters:
        from models.models import Group
        stmt = stmt.where(Attendance.group == Group(filters["group"]))
    if "dept" in filters:
        from models.models import Department
        stmt = stmt.where(UserModel.department == Department(filters["dept"]))
    if "period" in filters:
        days = {"7d": 7, "30d": 30}.get(filters["period"])
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            stmt = stmt.where(Attendance.date >= cutoff.date())

    await query.message.edit_text("Generating CSV…")

    async with async_session() as session:
        rows_data = (await session.execute(stmt.order_by(Attendance.date.desc(), Attendance.group))).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    headers = ["Date", "Group", "Name", "Surname", "Phone", "Department", "Enter At", "Left At"]
    w.writerow(headers)
    for r in rows_data:
        w.writerow([
            str(r.date), r.group.value, r.name, r.surname, r.phone,
            r.department.value, str(r.enter_at), str(r.left_at or ""),
        ])

    csv_bytes = buf.getvalue().encode("utf-8")
    buf_io = io.BytesIO(csv_bytes)
    buf_io.name = f"attendance_{uuid4().hex[:8]}.csv"
    await query.message.reply_document(document=buf_io, filename=buf_io.name, caption=f"📊 Attendance: {len(rows_data)} rows")
    del context.user_data["acsv_filters"]


csv_handlers = [
    CommandHandler("usercsv", csv_user_start),
    CommandHandler("attendcsv", attend_csv_start),
    CallbackQueryHandler(csv_callback, pattern="^csv:"),
    CallbackQueryHandler(acsv_callback, pattern="^acsv:"),
]
