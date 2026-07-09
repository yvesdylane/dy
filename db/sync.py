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
    try:
        return mapping[val]
    except KeyError:
        print(f"  \u26a0  Unknown {label} '{val}', skipping record")
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
    existing_phones = set()
    with SessionLocal() as session:
        for u in session.query(User).with_entities(User.id, User.telegram_id, User.phone).all():
            existing_by_tid[u.telegram_id] = u.id
            existing_phones.add(u.phone)

    to_insert_users = []
    user_old_ids = []
    seen_phones = set()
    for row in old_users:
        inc_read("user")
        tid = str(row["telegram_id"])
        if tid in existing_by_tid:
            id_map["user"][row["id"]] = existing_by_tid[tid]
            inc_skipped("user")
            continue
        dept = normalize_enum_value(row["department"], DEPARTMENT_MAP, "department")
        if dept is None:
            inc_error("user")
            continue
        gender = normalize_enum_value(row["gender"], GENDER_MAP, "gender")
        if gender is None:
            inc_error("user")
            continue
        role = normalize_enum_value(row["role"], ROLE_MAP, "role")
        if role is None:
            inc_error("user")
            continue
        phone = normalize_phone(row["phone"])
        if phone in existing_phones or phone in seen_phones:
            print(f"  \u26a0  User {row['id']}: duplicate phone '{phone}', skipping")
            inc_skipped("user")
            continue
        g_val = row["group"]
        group = normalize_enum_value(g_val, GROUP_MAP, "group") if g_val else None
        dob = parse_date(row["dob"])
        if not dob:
            print(f"  \u26a0  User {row['id']}: invalid dob '{row['dob']}', skipping")
            inc_error("user")
            continue
        seen_phones.add(phone)
        to_insert_users.append(User(
            name=row["name"],
            surname=row["surname"],
            email=None,
            phone=phone,
            telegram_id=tid,
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

    # ── 1b. Face embeddings ────────────────────────────────────
    report_lines.append("")
    report_lines.append("── Face embeddings ──────────────────────────────────────")
    pending: list[tuple[int, str]] = []
    with SessionLocal() as session:
        users_with_images = session.query(User).filter(
            User.image.isnot(None),
            User.image != "",
        ).all()
        existing_ids = {r[0] for r in session.query(FaceEmbedding.user_id).all()}
        for u in users_with_images:
            if u.id not in existing_ids:
                pending.append((u.id, u.image))

    emb_stats = {"created": 0, "no_face": 0, "dl_failed": 0}
    results: list[tuple[int, bytes]] = []
    for idx, (uid, image_val) in enumerate(pending, 1):
        img_bytes = download_image_bytes(image_val)
        if img_bytes is None:
            emb_stats["dl_failed"] += 1
            continue
        embedding = extract_embedding(img_bytes)
        if embedding is None:
            emb_stats["no_face"] += 1
            continue
        results.append((uid, embedding.tobytes()))
        emb_stats["created"] += 1

    with SessionLocal() as session:
        for uid, emb_bytes in results:
            session.add(FaceEmbedding(user_id=uid, embedding=emb_bytes))
        session.commit()

    report_lines.append(
        f"  {emb_stats['created']} created, "
        f"{emb_stats['no_face']} no-face, "
        f"{emb_stats['dl_failed']} dl-failed"
    )

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

    # ── Skipped tables ─────────────────────────────────────────
    for tname in ("cleaning_groups", "cleaning_group_members", "cleaning_duties", "cleaning_completions", "attendance_codes"):
        rows = sqlite_fetch_all(old, tname)
        if rows:
            report_lines.append("")
            report_lines.append(f"\u2500\u2500 {tname} \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
            report_lines.append(f"  Skipped ({len(rows)} record{plural(len(rows))} \u2014 table not in v2)")

    # ── Summary ────────────────────────────────────────────────
    report_lines.append("")
    report_lines.append("\u2550" * 55)
    report_lines.append("SUMMARY")
    report_lines.append("\u2550" * 55)
    total_read = 0
    total_inserted = 0
    total_skipped = 0
    total_errors = 0
    for table, s in stats.items():
        r = s.get("read", 0)
        i = s.get("inserted", 0)
        sk = s.get("skipped", 0)
        e = s.get("errors", 0)
        total_read += r
        total_inserted += i
        total_skipped += sk
        total_errors += e
        report_lines.append(f"  {table:20s}  {r:4d} read  \u2192  {i:4d} inserted  {sk:4d} skipped  {e:4d} errors")
    report_lines.append(f"  {'\u2500' * 50}")
    report_lines.append(f"  {'TOTAL':20s}  {total_read:4d} read  \u2192  {total_inserted:4d} inserted  {total_skipped:4d} skipped  {total_errors:4d} errors")

    old_conn.close()
    engine.dispose()

    return "\n".join(report_lines)
