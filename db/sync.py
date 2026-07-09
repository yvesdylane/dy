import logging
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from controllers.face import extract_embedding
from db.database import normalize_url
from models.attendance import Attendance, InternAttendance
from models.complaint import Complaint
from models.enums import ComplainType, Department, Gender, Group, LeaveStatus, Role
from models.infoNote import Info, Note
from models.leave import LeaveRequest
from models.task import Task, TaskSubmission
from models.user import CreationCode, FaceEmbedding, User
from helpers.phone import is_fake_telegram_id

logger = logging.getLogger(__name__)

DEPARTMENT_MAP = {
    "ISM": Department.ISM,
    "SWE": Department.SWE,
    "CGWD": Department.CGWD,
    "EDM": Department.EDM,
    "CSNW": Department.CSN,
    "DBM": Department.DBMS,
    "CNWS": Department.NWS,
    "NS": Department.NWS,
}

GENDER_MAP = {"male": Gender.male, "female": Gender.female}

ROLE_MAP = {
    "intern": Role.intern,
    "instructor": Role.instructor,
    "admin": Role.admin,
    "super_admin": Role.super_admin,
}

GROUP_MAP = {"A": Group.A, "B": Group.B}

COMPLAIN_TYPE_MAP = {"complaint": ComplainType.complaint, "advice": ComplainType.advice}

LEAVE_STATUS_MAP = {
    "pending": LeaveStatus.pending,
    "approved": LeaveStatus.approved,
    "rejected": LeaveStatus.rejected,
}

TELEGRAM_FILE_API = "https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
TELEGRAM_DL_API = "https://api.telegram.org/file/bot{token}/{file_path}"


def normalize_phone(raw):
    phone = raw.replace(" ", "")
    if phone.startswith("+"):
        return phone
    if phone.startswith("237"):
        return "+" + phone
    return "+237" + phone


def normalize_enum_value(val, mapping, label="value"):
    if val is None:
        return None
    if val in mapping:
        return mapping[val]
    # case-insensitive fallback
    val_lower = val.lower()
    for k, v in mapping.items():
        if k.lower() == val_lower:
            return v
    return None


def parse_date(val):
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        return datetime.strptime(val, "%Y-%m-%d").date()
    return None


def parse_datetime(val):
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
    return None


def parse_numeric(val):
    if val is None:
        return None
    return Decimal(str(val))


def _try_download(token: str, file_id: str) -> bytes | None:
    info_resp = httpx.get(
        TELEGRAM_FILE_API.format(token=token, file_id=file_id),
        timeout=15,
    )
    info_resp.raise_for_status()
    file_path = info_resp.json()["result"]["file_path"]
    dl_resp = httpx.get(
        TELEGRAM_DL_API.format(token=token, file_path=file_path),
        timeout=30,
    )
    dl_resp.raise_for_status()
    return dl_resp.content


def download_image_bytes(image_val: str) -> bytes | None:
    if image_val.startswith("http"):
        try:
            resp = httpx.get(image_val, timeout=30)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            print(f"  \u26a0  Failed to download URL: {e}")
            return None

    tokens = [settings.bot_token]
    if settings.old_bot_token:
        tokens.append(settings.old_bot_token)

    for token in tokens:
        try:
            return _try_download(token, image_val)
        except Exception:
            continue

    print(f"  \u26a0  Failed to download file_id (tried {len(tokens)} bot(s)): {image_val[:40]}...")
    return None


def sqlite_fetch_all(cursor, table, order_by="id"):
    if order_by:
        cursor.execute(f"SELECT * FROM {table} ORDER BY {order_by}")
    else:
        cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    return [dict(zip(col_names, row)) for row in rows]


def _user_label(row: dict) -> str:
    tid = row.get("telegram_id") or "?"
    name = row.get("name", "?")
    surname = row.get("surname", "?")
    return f"#{row['id']} {name} {surname} (tel:{tid})"


def sync_from_backup(backup_db_path: str) -> str:
    backup_path = Path(backup_db_path)
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_db_path}")

    old_conn = sqlite3.connect(str(backup_path))
    old_conn.row_factory = sqlite3.Row
    old = old_conn.cursor()

    url, connect_args = normalize_url(settings.database_url)
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine)

    id_map: dict[str, dict[int, int]] = {}
    stats: dict[str, dict[str, int]] = {}
    report_lines: list[str] = []

    def inc(table, key):
        s = stats.setdefault(table, {"read": 0, "inserted": 0, "skipped": 0, "errors": 0})
        s[key] = s.get(key, 0) + 1

    def inc_read(table):
        inc(table, "read")

    def inc_inserted(table):
        inc(table, "inserted")

    def inc_skipped(table):
        inc(table, "skipped")

    def inc_error(table):
        inc(table, "errors")

    def plural(n):
        return "s" if n != 1 else ""

    # ── 1. Users ───────────────────────────────────────────────
    report_lines.append("── Users ──────────────────────────────────────────────")
    id_map["user"] = {}
    old_users = sqlite_fetch_all(old, "users")
    existing_by_tid = {}
    existing_by_phone = {}
    with SessionLocal() as session:
        for u in session.query(User).with_entities(User.id, User.telegram_id, User.phone).all():
            if u.telegram_id and not is_fake_telegram_id(u.telegram_id):
                existing_by_tid[u.telegram_id] = u.id
            existing_by_phone[u.phone] = u.id

    to_insert_users = []
    user_old_ids = []
    seen_phones = set()
    user_messages: list[str] = []
    for row in old_users:
        inc_read("user")
        label = _user_label(row)
        tid = str(row["telegram_id"]) if row["telegram_id"] is not None else ""
        backup_has_valid_tid = bool(tid) and not is_fake_telegram_id(tid)
        if backup_has_valid_tid and tid in existing_by_tid:
            id_map["user"][row["id"]] = existing_by_tid[tid]
            inc_skipped("user")
            continue
        dept = normalize_enum_value(row["department"], DEPARTMENT_MAP, "department")
        if dept is None:
            user_messages.append(f"  \u274c {label}: unknown department '{row['department']}'")
            inc_error("user")
            continue
        gender = normalize_enum_value(row["gender"], GENDER_MAP, "gender")
        if gender is None:
            user_messages.append(f"  \u274c {label}: unknown gender '{row['gender']}'")
            inc_error("user")
            continue
        role = normalize_enum_value(row["role"], ROLE_MAP, "role")
        if role is None:
            user_messages.append(f"  \u274c {label}: unknown role '{row['role']}'")
            inc_error("user")
            continue
        phone = normalize_phone(row["phone"])
        if phone in existing_by_phone:
            existing_id = existing_by_phone[phone]
            tid_updated = False
            if backup_has_valid_tid:
                with SessionLocal() as session:
                    existing_user = session.query(User).filter(User.id == existing_id).first()
                    if existing_user and is_fake_telegram_id(existing_user.telegram_id):
                        old_tid = existing_user.telegram_id
                        existing_user.telegram_id = tid
                        session.commit()
                        tid_updated = True
                        user_messages.append(f"  \u2714  {label}: updated telegram_id '{old_tid}' \u2192 '{tid}'")
            if tid_updated:
                id_map["user"][row["id"]] = existing_id
            else:
                user_messages.append(f"  \u26a0  {label}: duplicate phone '{phone}', skipping")
            inc_skipped("user")
            continue
        if phone in seen_phones:
            user_messages.append(f"  \u26a0  {label}: duplicate phone '{phone}' in backup, skipping")
            inc_skipped("user")
            continue
        g_val = row["group"]
        group = normalize_enum_value(g_val, GROUP_MAP, "group") if g_val else None
        dob = parse_date(row["dob"])
        if not dob:
            user_messages.append(f"  \u274c {label}: invalid dob '{row['dob']}'")
            inc_error("user")
            continue
        seen_phones.add(phone)
        to_insert_users.append(User(
            name=row["name"],
            surname=row["surname"],
            email=None,
            phone=phone,
            telegram_id=tid or None,
            gender=gender,
            role=role,
            department=dept,
            group=group,
            school=row["school"] or "",
            dob=dob,
            image=row.get("image"),
            quarter=str(row["quarter"]) if row.get("quarter") is not None else None,
            fees_paid=parse_numeric(row.get("fees_paid")),
            total_fees=parse_numeric(row.get("total_fees")),
        ))
        user_old_ids.append(row["id"])

    if to_insert_users:
        with SessionLocal() as session:
            session.add_all(to_insert_users)
            session.flush()
            for old_id, new_user in zip(user_old_ids, to_insert_users):
                id_map["user"][old_id] = new_user.id
            session.commit()
    inc_inserted("user")
    stats["user"]["inserted"] = len(to_insert_users)
    report_lines.append(f"  {len(old_users)} read \u2192 {len(to_insert_users)} inserted, {len(old_users) - len(to_insert_users)} skipped")
    if user_messages:
        report_lines.append("")
        report_lines.extend(user_messages)

    # ── 1b. Face embeddings (disabled — 512MB RAM limit) ──────
    report_lines.append("")
    report_lines.append("── Face embeddings ──────────────────────────────────────")
    report_lines.append("  skipped (face recognition disabled)")

    # ── 2. Attendances ─────────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Attendances ─────────────────────────────────────────")
    id_map["attendance"] = {}
    old_attendances = sqlite_fetch_all(old, "attendances")
    existing_att_keys = {}
    with SessionLocal() as session:
        for a in session.query(Attendance).all():
            existing_att_keys[(a.date, a.group)] = a.id

    to_insert_att = []
    att_old_ids = []
    for row in old_attendances:
        inc_read("attendance")
        d = parse_date(row["date"])
        if not d:
            inc_error("attendance")
            continue
        group = normalize_enum_value(row["group"], GROUP_MAP, "group")
        if group is None:
            inc_error("attendance")
            continue
        key = (d, group)
        if key in existing_att_keys:
            id_map["attendance"][row["id"]] = existing_att_keys[key]
            inc_skipped("attendance")
            continue
        to_insert_att.append(Attendance(date=d, group=group))
        att_old_ids.append(row["id"])

    if to_insert_att:
        with SessionLocal() as session:
            session.add_all(to_insert_att)
            session.flush()
            for old_id, new_att in zip(att_old_ids, to_insert_att):
                id_map["attendance"][old_id] = new_att.id
            session.commit()
    inc_inserted("attendance")
    stats["attendance"]["inserted"] = len(to_insert_att)
    report_lines.append(f"  {len(old_attendances)} read \u2192 {len(to_insert_att)} inserted, {len(old_attendances) - len(to_insert_att)} skipped")

    # ── 3. Tasks ───────────────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Tasks ───────────────────────────────────────────────")
    id_map["task"] = {}
    old_tasks = sqlite_fetch_all(old, "tasks")
    existing_task_keys = {}
    with SessionLocal() as session:
        for t in session.query(Task).all():
            existing_task_keys[(t.name, t.department, t.submission_deadline)] = t.id

    to_insert_tasks = []
    task_old_ids = []
    for row in old_tasks:
        inc_read("task")
        dept = normalize_enum_value(row["department"], DEPARTMENT_MAP, "department")
        if dept is None:
            inc_error("task")
            continue
        deadline = parse_datetime(row["submission_deadline"])
        if not deadline:
            inc_error("task")
            continue
        mapped_creator = id_map.get("user", {}).get(row["created_by"])
        if not mapped_creator:
            print(f"  \u26a0  Task {row['id']}: creator user {row['created_by']} not synced, skipping")
            inc_skipped("task")
            continue
        key = (row["name"], dept, deadline)
        if key in existing_task_keys:
            id_map["task"][row["id"]] = existing_task_keys[key]
            inc_skipped("task")
            continue
        to_insert_tasks.append(Task(
            name=row["name"],
            description=row["description"],
            supporting_doc=row.get("supporting_doc"),
            file_id=row.get("file_id"),
            file_name=row.get("file_name"),
            department=dept,
            submission_deadline=deadline,
            total_mark_on=row["total_mark_on"],
            created_by=mapped_creator,
        ))
        task_old_ids.append(row["id"])

    if to_insert_tasks:
        with SessionLocal() as session:
            session.add_all(to_insert_tasks)
            session.flush()
            for old_id, new_task in zip(task_old_ids, to_insert_tasks):
                id_map["task"][old_id] = new_task.id
            session.commit()
    inc_inserted("task")
    stats["task"]["inserted"] = len(to_insert_tasks)
    report_lines.append(f"  {len(old_tasks)} read \u2192 {len(to_insert_tasks)} inserted, {len(old_tasks) - len(to_insert_tasks)} skipped")

    # ── 4. Creation codes ──────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Creation codes ──────────────────────────────────────")
    old_codes = sqlite_fetch_all(old, "creation_codes")
    existing_codes = set()
    with SessionLocal() as session:
        for c in session.query(CreationCode.code).all():
            existing_codes.add(c.code)

    to_insert_codes = []
    for row in old_codes:
        inc_read("creation_code")
        mapped_creator = id_map.get("user", {}).get(row["created_by"])
        if not mapped_creator:
            inc_skipped("creation_code")
            continue
        role = normalize_enum_value(row["role"], ROLE_MAP, "role")
        if role is None:
            inc_error("creation_code")
            continue
        expires_at = parse_datetime(row["expires_at"])
        if not expires_at:
            inc_error("creation_code")
            continue
        if row["code"] in existing_codes:
            inc_skipped("creation_code")
            continue
        to_insert_codes.append(CreationCode(
            code=row["code"],
            role=role,
            expires_at=expires_at,
            is_used=bool(row["is_used"]),
            created_by=mapped_creator,
        ))

    if to_insert_codes:
        with SessionLocal() as session:
            session.add_all(to_insert_codes)
            session.commit()
    inc_inserted("creation_code")
    stats["creation_code"]["inserted"] = len(to_insert_codes)
    report_lines.append(f"  {len(old_codes)} read \u2192 {len(to_insert_codes)} inserted, {len(old_codes) - len(to_insert_codes)} skipped")

    # ── 5. Intern attendances ──────────────────────────────────
    report_lines.append("")
    report_lines.append("── Intern attendances ──────────────────────────────────")
    old_ia = sqlite_fetch_all(old, "intern_attendances", order_by=None)
    existing_pairs = set()
    with SessionLocal() as session:
        rows = session.query(InternAttendance.attendance_id, InternAttendance.user_id).all()
        existing_pairs = {(r.attendance_id, r.user_id) for r in rows}

    to_insert_ia = []
    for row in old_ia:
        inc_read("intern_attendance")
        mapped_att_id = id_map.get("attendance", {}).get(row["attendance_id"])
        mapped_user_id = id_map.get("user", {}).get(row["user_id"])
        if not mapped_att_id or not mapped_user_id:
            inc_skipped("intern_attendance")
            continue
        if (mapped_att_id, mapped_user_id) in existing_pairs:
            inc_skipped("intern_attendance")
            continue
        enter_at = parse_datetime(row["enter_at"])
        left_at = parse_datetime(row["left_at"]) if row.get("left_at") else None
        to_insert_ia.append({
            "attendance_id": mapped_att_id,
            "user_id": mapped_user_id,
            "enter_at": enter_at,
            "left_at": left_at,
            "status": row.get("status"),
        })

    if to_insert_ia:
        with SessionLocal() as session:
            session.bulk_insert_mappings(InternAttendance, to_insert_ia)
            session.commit()
    inc_inserted("intern_attendance")
    stats["intern_attendance"]["inserted"] = len(to_insert_ia)
    report_lines.append(f"  {len(old_ia)} read \u2192 {len(to_insert_ia)} inserted, {len(old_ia) - len(to_insert_ia)} skipped")

    # ── 6. Task submissions ────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Task submissions ────────────────────────────────────")
    old_submissions = sqlite_fetch_all(old, "task_submissions")
    existing_ts_pairs = set()
    with SessionLocal() as session:
        rows = session.query(TaskSubmission.task_id, TaskSubmission.user_id).all()
        existing_ts_pairs = {(r.task_id, r.user_id) for r in rows}

    to_insert_ts = []
    for row in old_submissions:
        inc_read("task_submission")
        mapped_task_id = id_map.get("task", {}).get(row["task_id"])
        mapped_user_id = id_map.get("user", {}).get(row["user_id"])
        if not mapped_task_id or not mapped_user_id:
            inc_skipped("task_submission")
            continue
        if (mapped_task_id, mapped_user_id) in existing_ts_pairs:
            inc_skipped("task_submission")
            continue
        to_insert_ts.append({
            "task_id": mapped_task_id,
            "user_id": mapped_user_id,
            "submitted_file": row.get("submitted_file"),
            "file_id": row.get("file_id"),
            "file_name": row.get("file_name"),
            "submitted_url": row.get("submitted_url"),
            "mark_obtained": parse_numeric(row.get("mark_obtained")),
            "feedback": row.get("feedback"),
        })

    if to_insert_ts:
        with SessionLocal() as session:
            session.bulk_insert_mappings(TaskSubmission, to_insert_ts)
            session.commit()
    stats["task_submission"]["inserted"] = len(to_insert_ts)
    report_lines.append(f"  {len(old_submissions)} read \u2192 {len(to_insert_ts)} inserted, {len(old_submissions) - len(to_insert_ts)} skipped")

    # ── 7. Infos ───────────────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Infos ───────────────────────────────────────────────")
    old_infos = sqlite_fetch_all(old, "infos")
    existing_info_keys = set()
    with SessionLocal() as session:
        for info in session.query(Info.title, Info.created_at).all():
            existing_info_keys.add((info.title, info.created_at))

    to_insert_infos = []
    for row in old_infos:
        inc_read("info")
        mapped_creator = id_map.get("user", {}).get(row["created_by"])
        if not mapped_creator:
            inc_skipped("info")
            continue
        created_at = parse_datetime(row["created_at"])
        if (row["title"], created_at) in existing_info_keys:
            inc_skipped("info")
            continue
        to_insert_infos.append(Info(
            title=row["title"],
            content=row["content"],
            file_url=row.get("file_url") or row.get("file_id"),
            file_id=row.get("file_id"),
            file_name=row.get("file_name"),
            created_by=mapped_creator,
            created_at=created_at,
            updated_at=parse_datetime(row.get("updated_at")),
        ))

    if to_insert_infos:
        with SessionLocal() as session:
            session.add_all(to_insert_infos)
            session.commit()
    inc_inserted("info")
    stats["info"]["inserted"] = len(to_insert_infos)
    report_lines.append(f"  {len(old_infos)} read \u2192 {len(to_insert_infos)} inserted, {len(old_infos) - len(to_insert_infos)} skipped")

    # ── 8. Notes ───────────────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Notes ───────────────────────────────────────────────")
    old_notes = sqlite_fetch_all(old, "notes")
    existing_note_keys = set()
    with SessionLocal() as session:
        for note in session.query(Note.title, Note.department, Note.created_at).all():
            existing_note_keys.add((note.title, note.department, note.created_at))

    to_insert_notes = []
    for row in old_notes:
        inc_read("note")
        mapped_uploader = id_map.get("user", {}).get(row["uploaded_by"])
        if not mapped_uploader:
            inc_skipped("note")
            continue
        dept = normalize_enum_value(row["department"], DEPARTMENT_MAP, "department") if row.get("department") else None
        created_at = parse_datetime(row["created_at"])
        if (row["title"], dept, created_at) in existing_note_keys:
            inc_skipped("note")
            continue
        to_insert_notes.append(Note(
            title=row["title"],
            content=row.get("content"),
            file_url=row.get("file_url") or row.get("file_id"),
            file_id=row.get("file_id"),
            file_name=row.get("file_name"),
            department=dept,
            uploaded_by=mapped_uploader,
            created_at=created_at,
            updated_at=parse_datetime(row.get("updated_at")),
        ))

    if to_insert_notes:
        with SessionLocal() as session:
            session.add_all(to_insert_notes)
            session.commit()
    inc_inserted("note")
    stats["note"]["inserted"] = len(to_insert_notes)
    report_lines.append(f"  {len(old_notes)} read \u2192 {len(to_insert_notes)} inserted, {len(old_notes) - len(to_insert_notes)} skipped")

    # ── 9. Complaints ──────────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Complaints ──────────────────────────────────────────")
    old_complaints = sqlite_fetch_all(old, "user_complains")
    existing_complaint_keys = set()
    with SessionLocal() as session:
        for c in session.query(Complaint.content, Complaint.created_at).all():
            existing_complaint_keys.add((c.content, c.created_at))

    to_insert_complaints = []
    for row in old_complaints:
        inc_read("complaint")
        dept = normalize_enum_value(row["department"], DEPARTMENT_MAP, "department")
        if dept is None:
            inc_error("complaint")
            continue
        ctype = normalize_enum_value(row["complain_type"], COMPLAIN_TYPE_MAP, "complain_type")
        if ctype is None:
            inc_error("complaint")
            continue
        group = normalize_enum_value(row["group"], GROUP_MAP, "group") if row.get("group") else None
        created_at = parse_datetime(row["created_at"])
        if (row["content"], created_at) in existing_complaint_keys:
            inc_skipped("complaint")
            continue
        to_insert_complaints.append(Complaint(
            content=row["content"],
            complain_type=ctype,
            department=dept,
            group=group,
            created_at=created_at,
        ))

    if to_insert_complaints:
        with SessionLocal() as session:
            session.add_all(to_insert_complaints)
            session.commit()
    inc_inserted("complaint")
    stats["complaint"]["inserted"] = len(to_insert_complaints)
    report_lines.append(f"  {len(old_complaints)} read \u2192 {len(to_insert_complaints)} inserted, {len(old_complaints) - len(to_insert_complaints)} skipped")

    # ── 10. Leave requests ────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Leave requests ──────────────────────────────────────")
    old_leaves = sqlite_fetch_all(old, "leave_requests")
    existing_leave_keys = set()
    with SessionLocal() as session:
        for lr in session.query(LeaveRequest.user_id, LeaveRequest.date).all():
            existing_leave_keys.add((lr.user_id, lr.date))

    to_insert_leaves = []
    for row in old_leaves:
        inc_read("leave_request")
        mapped_user_id = id_map.get("user", {}).get(row["user_id"])
        if not mapped_user_id:
            inc_skipped("leave_request")
            continue
        d = parse_date(row["date"])
        if not d:
            inc_error("leave_request")
            continue
        if (mapped_user_id, d) in existing_leave_keys:
            inc_skipped("leave_request")
            continue
        status = normalize_enum_value(row["status"], LEAVE_STATUS_MAP, "leave_status") if row.get("status") else None
        mapped_reviewer = id_map.get("user", {}).get(row["reviewed_by"]) if row.get("reviewed_by") else None
        to_insert_leaves.append(LeaveRequest(
            user_id=mapped_user_id,
            date=d,
            reason=row["reason"],
            status=status,
            reviewed_by=mapped_reviewer,
        ))

    if to_insert_leaves:
        with SessionLocal() as session:
            session.add_all(to_insert_leaves)
            session.commit()
    inc_inserted("leave_request")
    stats["leave_request"]["inserted"] = len(to_insert_leaves)
    report_lines.append(f"  {len(old_leaves)} read \u2192 {len(to_insert_leaves)} inserted, {len(old_leaves) - len(to_insert_leaves)} skipped")

    # ── Build compact report ───────────────────────────────────
    report_lines = ["✅ Sync complete\n"]

    # skipped old tables
    old_skipped = []
    for tname in ("cleaning_groups", "cleaning_group_members", "cleaning_duties", "cleaning_completions", "attendance_codes"):
        try:
            rows = sqlite_fetch_all(old, tname)
        except sqlite3.OperationalError:
            continue
        if rows:
            short = tname.replace("cleaning_completions", "clean_completions").replace("cleaning_group_members", "clean_members").replace("cleaning_duties", "clean_duties").replace("cleaning_groups", "clean_groups").replace("attendance_codes", "att_codes")
            old_skipped.append(f"{short} ({len(rows)})")
    if old_skipped:
        report_lines.append(f"\u23ed Old tables ignored: {', '.join(old_skipped)}\n")

    total_inserted = 0
    total_skipped = 0
    total_errors = 0
    for table, s in stats.items():
        i = s.get("inserted", 0)
        sk = s.get("skipped", 0)
        e = s.get("errors", 0)
        if i == 0 and sk == 0:
            continue
        total_inserted += i
        total_skipped += sk
        total_errors += e
        parts = [str(i)]
        if sk: parts.append(f"{sk} \u26a0")
        if e: parts.append(f"{e} \u274c")
        report_lines.append(f"  {table}: {' \u00b7 '.join(parts)}")

    summary = f"\n  Total: {total_inserted} imported"
    if total_skipped:
        summary += f" \u00b7 {total_skipped} skipped"
    if total_errors:
        summary += f" \u00b7 {total_errors} errors"
    report_lines.append(summary)

    old_conn.close()
    engine.dispose()

    return "\n".join(report_lines)


def sync_user_attendance_data(backup_db_path: str) -> str:
    """Sync only users, attendances, leave requests, and task submissions.

    Matches backup users to existing DB users by phone (primary) or telegram_id.
    Updates existing users' telegram_id if backup has a valid one. Only imports
    attendance, leave, and submission records for matched users — no new users created.
    """
    backup_path = Path(backup_db_path)
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_db_path}")

    old_conn = sqlite3.connect(str(backup_path))
    old_conn.row_factory = sqlite3.Row
    old = old_conn.cursor()

    url, connect_args = normalize_url(settings.database_url)
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine)

    id_map: dict[str, dict[int, int]] = {"user": {}}
    stats: dict[str, dict[str, int]] = {}
    report_lines: list[str] = []

    def inc(table, key):
        s = stats.setdefault(table, {"read": 0, "matched": 0, "inserted": 0, "skipped": 0, "errors": 0})
        s[key] = s.get(key, 0) + 1

    # ── 1. Match users by phone, then telegram_id ──────────────
    report_lines.append("── Users ──────────────────────────────────────────────")
    old_users = sqlite_fetch_all(old, "users")

    existing_by_phone = {}
    existing_by_tid = {}
    with SessionLocal() as session:
        for u in session.query(User).with_entities(User.id, User.telegram_id, User.phone).all():
            existing_by_phone[u.phone] = u.id
            if u.telegram_id and not is_fake_telegram_id(u.telegram_id):
                existing_by_tid[u.telegram_id] = u.id

    matched = 0
    tid_updated = 0
    unmatched = 0
    for row in old_users:
        inc("user", "read")
        phone = normalize_phone(row["phone"])
        tid = str(row["telegram_id"]) if row["telegram_id"] is not None else ""
        backup_has_valid_tid = bool(tid) and not is_fake_telegram_id(tid)

        existing_id = existing_by_phone.get(phone)

        if existing_id is None and backup_has_valid_tid:
            existing_id = existing_by_tid.get(tid)

        if existing_id is not None:
            id_map["user"][row["id"]] = existing_id
            matched += 1
            inc("user", "matched")

            if backup_has_valid_tid:
                with SessionLocal() as session:
                    u = session.query(User).filter(User.id == existing_id).first()
                    if u and is_fake_telegram_id(u.telegram_id):
                        u.telegram_id = tid
                        session.commit()
                        tid_updated += 1
        else:
            unmatched += 1
            inc("user", "skipped")

    report_lines.append(f"  {len(old_users)} read → {matched} matched, {unmatched} unmatched")
    if tid_updated:
        report_lines.append(f"  ↳ {tid_updated} telegram_id(s) updated from backup")

    # ── 2. Attendances + Intern attendances ─────────────────────
    report_lines.append("")
    report_lines.append("── Attendances ────────────────────────────────────────")
    id_map["attendance"] = {}
    old_attendances = sqlite_fetch_all(old, "attendances")
    existing_att_keys = {}
    with SessionLocal() as session:
        for a in session.query(Attendance).all():
            existing_att_keys[(a.date, a.group)] = a.id

    to_insert_att = []
    att_old_ids = []
    for row in old_attendances:
        inc("attendance", "read")
        d = parse_date(row["date"])
        if not d:
            inc("attendance", "errors")
            continue
        group = normalize_enum_value(row["group"], GROUP_MAP, "group")
        if group is None:
            inc("attendance", "errors")
            continue
        key = (d, group)
        if key in existing_att_keys:
            id_map["attendance"][row["id"]] = existing_att_keys[key]
            inc("attendance", "skipped")
            continue
        to_insert_att.append(Attendance(date=d, group=group))
        att_old_ids.append(row["id"])

    if to_insert_att:
        with SessionLocal() as session:
            session.add_all(to_insert_att)
            session.flush()
            for old_id, new_att in zip(att_old_ids, to_insert_att):
                id_map["attendance"][old_id] = new_att.id
            session.commit()
    stats["attendance"]["inserted"] = len(to_insert_att)
    report_lines.append(f"  {len(old_attendances)} read → {len(to_insert_att)} new, {len(old_attendances) - len(to_insert_att)} existing")

    # ── 2b. Intern attendances ──────────────────────────────────
    report_lines.append("")
    report_lines.append("── Intern attendances ──────────────────────────────────")
    old_ia = sqlite_fetch_all(old, "intern_attendances", order_by=None)
    existing_pairs = set()
    with SessionLocal() as session:
        for r in session.query(InternAttendance.attendance_id, InternAttendance.user_id).all():
            existing_pairs.add((r.attendance_id, r.user_id))

    to_insert_ia = []
    for row in old_ia:
        inc("intern_attendance", "read")
        mapped_att_id = id_map.get("attendance", {}).get(row["attendance_id"])
        mapped_user_id = id_map.get("user", {}).get(row["user_id"])
        if not mapped_att_id or not mapped_user_id:
            inc("intern_attendance", "skipped")
            continue
        if (mapped_att_id, mapped_user_id) in existing_pairs:
            inc("intern_attendance", "skipped")
            continue
        to_insert_ia.append({
            "attendance_id": mapped_att_id,
            "user_id": mapped_user_id,
            "enter_at": parse_datetime(row["enter_at"]),
            "left_at": parse_datetime(row["left_at"]) if row.get("left_at") else None,
            "status": row.get("status"),
        })

    if to_insert_ia:
        with SessionLocal() as session:
            session.bulk_insert_mappings(InternAttendance, to_insert_ia)
            session.commit()
    stats["intern_attendance"]["inserted"] = len(to_insert_ia)
    report_lines.append(f"  {len(old_ia)} read → {len(to_insert_ia)} imported")

    # ── 3. Leave requests ──────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Leave requests ──────────────────────────────────────")
    old_leaves = sqlite_fetch_all(old, "leave_requests")
    existing_leave_keys = set()
    with SessionLocal() as session:
        for lr in session.query(LeaveRequest.user_id, LeaveRequest.date).all():
            existing_leave_keys.add((lr.user_id, lr.date))

    to_insert_leaves = []
    for row in old_leaves:
        inc("leave_request", "read")
        mapped_user_id = id_map.get("user", {}).get(row["user_id"])
        if not mapped_user_id:
            inc("leave_request", "skipped")
            continue
        d = parse_date(row["date"])
        if not d:
            inc("leave_request", "errors")
            continue
        if (mapped_user_id, d) in existing_leave_keys:
            inc("leave_request", "skipped")
            continue
        status = normalize_enum_value(row.get("status"), LEAVE_STATUS_MAP, "leave_status") if row.get("status") else None
        mapped_reviewer = id_map.get("user", {}).get(row["reviewed_by"]) if row.get("reviewed_by") else None
        to_insert_leaves.append(LeaveRequest(
            user_id=mapped_user_id,
            date=d,
            reason=row["reason"],
            status=status,
            reviewed_by=mapped_reviewer,
        ))

    if to_insert_leaves:
        with SessionLocal() as session:
            session.add_all(to_insert_leaves)
            session.commit()
    stats["leave_request"]["inserted"] = len(to_insert_leaves)
    report_lines.append(f"  {len(old_leaves)} read → {len(to_insert_leaves)} imported")

    # ── 4. Tasks (for task_id mapping) ──────────────────────────
    report_lines.append("")
    report_lines.append("── Tasks ───────────────────────────────────────────────")
    id_map["task"] = {}
    old_tasks = sqlite_fetch_all(old, "tasks")
    existing_task_keys = {}
    with SessionLocal() as session:
        for t in session.query(Task).all():
            existing_task_keys[(t.name, t.department, t.submission_deadline)] = t.id

    task_created = 0
    for row in old_tasks:
        dept = normalize_enum_value(row["department"], DEPARTMENT_MAP, "department")
        if dept is None:
            continue
        deadline = parse_datetime(row["submission_deadline"])
        if not deadline:
            continue
        mapped_creator = id_map.get("user", {}).get(row["created_by"])
        key = (row["name"], dept, deadline)
        if key in existing_task_keys:
            id_map["task"][row["id"]] = existing_task_keys[key]
            continue
        if not mapped_creator:
            continue
        new_task = Task(
            name=row["name"],
            description=row["description"],
            supporting_doc=row.get("supporting_doc"),
            file_id=row.get("file_id"),
            file_name=row.get("file_name"),
            department=dept,
            submission_deadline=deadline,
            total_mark_on=row["total_mark_on"],
            created_by=mapped_creator,
        )
        with SessionLocal() as session:
            session.add(new_task)
            session.flush()
            id_map["task"][row["id"]] = new_task.id
            session.commit()
            task_created += 1
    report_lines.append(f"  {len(old_tasks)} read → {task_created} new tasks")

    # ── 5. Task submissions ────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Task submissions ────────────────────────────────────")
    old_submissions = sqlite_fetch_all(old, "task_submissions")
    existing_ts_pairs = set()
    with SessionLocal() as session:
        for r in session.query(TaskSubmission.task_id, TaskSubmission.user_id).all():
            existing_ts_pairs.add((r.task_id, r.user_id))

    to_insert_ts = []
    for row in old_submissions:
        inc("task_submission", "read")
        mapped_task_id = id_map.get("task", {}).get(row["task_id"])
        mapped_user_id = id_map.get("user", {}).get(row["user_id"])
        if not mapped_task_id or not mapped_user_id:
            inc("task_submission", "skipped")
            continue
        if (mapped_task_id, mapped_user_id) in existing_ts_pairs:
            inc("task_submission", "skipped")
            continue
        to_insert_ts.append({
            "task_id": mapped_task_id,
            "user_id": mapped_user_id,
            "submitted_file": row.get("submitted_file"),
            "file_id": row.get("file_id"),
            "file_name": row.get("file_name"),
            "submitted_url": row.get("submitted_url"),
            "mark_obtained": parse_numeric(row.get("mark_obtained")),
            "feedback": row.get("feedback"),
        })

    if to_insert_ts:
        with SessionLocal() as session:
            session.bulk_insert_mappings(TaskSubmission, to_insert_ts)
            session.commit()
    stats["task_submission"]["inserted"] = len(to_insert_ts)
    report_lines.append(f"  {len(old_submissions)} read → {len(to_insert_ts)} imported")

    # ── Build compact report ───────────────────────────────────
    report_lines = ["✅ User/attendance sync complete\n"]
    total_imported = 0
    for table, s in stats.items():
        i = s.get("inserted", 0)
        r = s.get("read", 0)
        if r == 0 and i == 0:
            continue
        total_imported += i
        parts = [str(i)]
        sk = s.get("skipped", 0)
        if sk:
            parts.append(f"{sk} ⚠")
        e = s.get("errors", 0)
        if e:
            parts.append(f"{e} ❌")
        report_lines.append(f"  {table}: {' · '.join(parts)}")
    report_lines.append(f"\n  Total: {total_imported} records imported")

    old_conn.close()
    engine.dispose()

    return "\n".join(report_lines)
