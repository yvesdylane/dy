from sqlalchemy import select

from models.enums import Role
from models.user import User


def fetch_interns(session) -> list[dict]:
    users = session.execute(
        select(User)
        .where(User.role == Role.intern)
        .order_by(User.department, User.group, User.surname, User.name)
    ).scalars().all()

    return [
        {
            "name": user.name,
            "surname": user.surname,
            "phone": user.phone,
            "email": user.email or "",
            "gender": user.gender.value if user.gender else "",
            "department": user.department.value if user.department else "",
            "group": user.group.value if user.group else "",
            "school": user.school,
            "dob": user.dob.isoformat() if user.dob else "",
            "quarter": user.quarter or "",
            "fees_paid": float(user.fees_paid or 0),
            "total_fees": float(user.total_fees or 0),
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else "",
        }
        for user in users
    ]
