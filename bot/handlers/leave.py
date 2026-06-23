from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from bot.handlers.common import get_user, logger

LEAVE_DATE, LEAVE_REASON = range(2)


async def cancel(update: Update, _context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def _get_group(d):
    from models.models import Group
    if d.weekday() == 6:
        return None
    return Group.A if d.weekday() in (0, 2, 4) else Group.B


async def leave_start(update: Update, context):
    from models.models import Role

    user = await get_user(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("User not found.")
        return ConversationHandler.END

    if user.role == Role.intern:
        return await _leave_pick_date(update, context, user)
    else:
        await _leave_show_list(update, context)
        return ConversationHandler.END


async def _leave_pick_date(update: Update, context, user):
    from datetime import date, timedelta

    today = date.today()
    rows = []
    row = []
    for i in range(1, 15):
        d = today + timedelta(days=i)
        grp = _get_group(d)
        if grp and grp == user.group:
            label = d.strftime("%a %d %b")
            row.append(InlineKeyboardButton(label, callback_data=f"leave_date_{d.isoformat()}"))
            if len(row) == 3:
                rows.append(row)
                row = []
    if row:
        rows.append(row)

    if not rows:
        await update.message.reply_text("No available dates for leave in the next 2 weeks.")
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup(rows + [[InlineKeyboardButton("Cancel", callback_data="leave_cancel")]])
    await update.message.reply_text("Select the date you want leave for:", reply_markup=keyboard)
    return LEAVE_DATE


async def leave_date_chosen(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "leave_cancel":
        await query.message.edit_text("Cancelled.")
        return ConversationHandler.END

    context.user_data["leave_date"] = data.split("_")[-1]
    await query.message.edit_text("What's the reason for your leave? (Send /cancel to cancel)")
    return LEAVE_REASON


async def leave_reason_received(update: Update, context):
    from datetime import date

    from db.database import async_session
    from models.models import LeaveRequest, LeaveStatus

    reason = update.message.text
    leave_date = context.user_data.get("leave_date")
    if not leave_date:
        await update.message.reply_text("Something went wrong. Use /leave to start over.")
        return ConversationHandler.END

    user = await get_user(str(update.effective_user.id))
    if not user:
        await update.message.reply_text("User not found.")
        return ConversationHandler.END

    async with async_session() as session:
        async with session.begin():
            session.add(LeaveRequest(
                user_id=user.id,
                date=date.fromisoformat(leave_date),
                reason=reason,
            ))

    await update.message.reply_text(
        f"✅ Leave request submitted for *{leave_date}*. Waiting for approval.",
        parse_mode="Markdown",
    )
    context.user_data.pop("leave_date", None)
    return ConversationHandler.END


async def _leave_show_list(update: Update, context):
    from models.models import LeaveRequest, LeaveStatus

    async with async_session() as session:
        pending = (await session.execute(
            select(LeaveRequest)
            .options(selectinload(LeaveRequest.user))
            .where(LeaveRequest.status == LeaveStatus.pending)
            .order_by(LeaveRequest.created_at.desc())
        )).scalars().all()

    if not pending:
        text = "No pending leave requests."
        if update.callback_query:
            await update.callback_query.message.edit_text(text)
        else:
            await update.message.reply_text(text)
        return

    keyboard = []
    for lr in pending:
        name_part = lr.user.name.split()[0] if lr.user and lr.user.name else f"User#{lr.user_id}"
        keyboard.append([InlineKeyboardButton(name_part, callback_data=f"leave_view_{lr.id}")])
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="leave_cancel")])

    markup = InlineKeyboardMarkup(keyboard)
    text = f"*Pending leave requests ({len(pending)}):*"

    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


async def leave_view(update: Update, context):
    from db.database import async_session
    from models.models import LeaveRequest

    query = update.callback_query
    await query.answer()

    lr_id = int(query.data.split("_")[-1])

    async with async_session() as session:
        lr = (await session.execute(
            select(LeaveRequest).options(selectinload(LeaveRequest.user)).where(LeaveRequest.id == lr_id)
        )).scalar_one_or_none()
        if not lr:
            await query.message.edit_text("Leave request not found.")
            return
        user = lr.user

    lines = [
        f"👤 {user.name} {user.surname}",
        f"📂 {user.department.value}{f' · Group {user.group.value}' if user.group else ''}",
        f"📅 {lr.date.isoformat()}",
        f"💬 {lr.reason}",
        f"📌 Status: *{lr.status.value.upper()}*",
    ]
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"leave_approve_{lr.id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"leave_reject_{lr.id}")],
        [InlineKeyboardButton("← Back", callback_data="leave_list")],
    ]
    await query.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def leave_review(update: Update, context):
    from datetime import datetime

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from db.database import async_session
    from models.models import Attendance, InternAttendance, LeaveRequest, LeaveStatus, User, Role

    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    action = parts[1]
    lr_id = int(parts[2])
    new_status = "approved" if action == "approve" else "rejected"

    async with async_session() as session:
        async with session.begin():
            lr = await session.execute(
                select(LeaveRequest)
                .options(selectinload(LeaveRequest.user))
                .where(LeaveRequest.id == lr_id)
            )
            lr = lr.scalar_one_or_none()
            if not lr:
                await query.message.edit_text("Leave request not found.")
                return

            reviewer = (await session.execute(
                select(User).where(User.telegram_id == str(query.from_user.id), User.role.in_([Role.admin, Role.instructor]))
            )).scalar_one_or_none()

            lr.status = LeaveStatus(new_status)
            if reviewer:
                lr.reviewed_by = reviewer.id

            intern_user = lr.user
            leave_date = lr.date

            if new_status == "approved":
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

    await query.message.edit_text(
        f"{'✅' if new_status == 'approved' else '❌'} Leave for *{intern_user.name}* on *{leave_date}* {new_status}.",
        parse_mode="Markdown",
    )

    from bot.router import application
    try:
        if intern_user and intern_user.telegram_id:
            emoji = "✅" if new_status == "approved" else "❌"
            await application.bot.send_message(
                chat_id=int(intern_user.telegram_id),
                text=(
                    f"Your leave request for *{leave_date.isoformat()}* has been *{new_status}*.\n\n"
                    f"Reason: {lr.reason}"
                ),
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.warning("Failed to notify intern about leave: %s", e)

    update.callback_query = query
    update.message = query.message
    await _leave_show_list(update, context)


leave_conv = ConversationHandler(
    entry_points=[CommandHandler("leave", leave_start)],
    states={
        LEAVE_DATE: [CallbackQueryHandler(leave_date_chosen, pattern=r"^leave_date_\d{4}-\d{2}-\d{2}$|^leave_cancel$")],
        LEAVE_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_reason_received)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


leave_handlers = [
    leave_conv,
    CallbackQueryHandler(leave_view, pattern=r"^leave_view_\d+$"),
    CallbackQueryHandler(leave_review, pattern=r"^leave_(approve|reject)_\d+$"),
    CallbackQueryHandler(_leave_show_list, pattern="^leave_list$"),
]
