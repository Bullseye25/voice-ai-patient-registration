"""
Patient SQLAlchemy Database Model
"""
import uuid
from datetime import datetime, date, timezone
from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Enum as SQLEnum,
    Index
)
from app.core.database import Base
import enum


class SexEnum(str, enum.Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    DECLINE_TO_ANSWER = "Decline to Answer"


def utc_now():
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"

    # Primary Key - Auto-generated UUIDv4
    patient_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )

    # Required Demographics
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False, index=True)
    date_of_birth = Column(Date, nullable=False, index=True)
    sex = Column(SQLEnum(SexEnum), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)

    # Optional Contact & Address
    email = Column(String(255), nullable=True)
    address_line_1 = Column(String(255), nullable=False)
    address_line_2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)

    # Optional Insurance & Language
    insurance_provider = Column(String(100), nullable=True)
    insurance_member_id = Column(String(50), nullable=True)
    preferred_language = Column(String(50), default="English", nullable=True)

    # Optional Emergency Contact
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)

    # Timestamps & Soft Deletion
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at = Column(DateTime, nullable=True, default=None, index=True)

    # Composite index for search by phone, last_name, date_of_birth
    __table_args__ = (
        Index("idx_patient_search", "last_name", "date_of_birth", "phone_number"),
    )

    def to_dict(self):
        """Helper to convert model to dictionary representation."""
        return {
            "patient_id": self.patient_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth.isoformat() if isinstance(self.date_of_birth, (date, datetime)) else self.date_of_birth,
            "sex": self.sex.value if isinstance(self.sex, SexEnum) else self.sex,
            "phone_number": self.phone_number,
            "email": self.email,
            "address_line_1": self.address_line_1,
            "address_line_2": self.address_line_2,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "insurance_provider": self.insurance_provider,
            "insurance_member_id": self.insurance_member_id,
            "preferred_language": self.preferred_language,
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
