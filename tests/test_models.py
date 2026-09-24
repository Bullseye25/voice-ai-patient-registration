"""
Unit Tests for SQLAlchemy Patient Model & Persistence Foundation
"""
import uuid
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.patient import Patient, SexEnum


def test_patient_model_creation():
    """Assert Patient model instantiation, default UUID, and serialization."""
    # In-memory SQLite engine for testing model
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(bind=test_engine)
    db = TestingSession()

    patient = Patient(
        first_name="Jane",
        last_name="Doe",
        date_of_birth=date(1992, 8, 20),
        sex=SexEnum.FEMALE,
        phone_number="5551112233",
        address_line_1="100 Main St",
        city="Austin",
        state="TX",
        zip_code="78701",
        insurance_provider="Aetna",
        preferred_language="English"
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    # Assertions
    assert patient.patient_id is not None
    assert len(patient.patient_id) == 36  # UUID string format
    assert patient.first_name == "Jane"
    assert patient.last_name == "Doe"
    assert patient.created_at is not None
    assert patient.updated_at is not None
    assert patient.deleted_at is None

    # Test dictionary serialization
    p_dict = patient.to_dict()
    assert p_dict["patient_id"] == patient.patient_id
    assert p_dict["first_name"] == "Jane"
    assert p_dict["sex"] == "Female"
    assert p_dict["deleted_at"] is None

    db.close()
