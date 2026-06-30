import enum


class Gender(enum.Enum):
    male = "male"
    female = "female"


class Role(enum.Enum):
    intern = "intern"
    instructor = "instructor"
    admin = "admin"
    super_admin = "super_admin"


class Department(enum.Enum):
    ISM = "ISM"
    SWE = "SWE"
    CGWD = "CGWD"
    EDM = "EDM"
    CSN = "CSN"
    DBMS = "DBMS"
    NWS = "NWS"


class Group(enum.Enum):
    A = "A"
    B = "B"


class ComplainType(enum.Enum):
    complaint = "complaint"
    advice = "advice"


class LeaveStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
