"""
Unit Tests for Patient Demographic Validation Engine
Verifies U.S. Healthcare Minimum Demographic Dataset Constraints
"""
import pytest
from datetime import date, timedelta
from pydantic import ValidationError
from app.schemas.patient import PatientCreate, PatientUpdate, SexEnum


@pytest.fixture
def valid_patient_payload():
    return {
        "first_name": "Sarah",
        "last_name": "Connor",
        "date_of_birth": "05/14/1985",
        "sex": "Female",
        "phone_number": "555-123-4567",
        "email": "sarah.connor@example.com",
        "address_line_1": "123 SkyNet Way",
        "address_line_2": "Suite 4B",
        "city": "Los Angeles",
        "state": "CA",
        "zip_code": "90001",
        "insurance_provider": "Blue Cross Blue Shield",
        "insurance_member_id": "BCBS-987654321",
        "preferred_language": "English",
        "emergency_contact_name": "John Connor",
        "emergency_contact_phone": "(555) 987-6543"
    }


def test_valid_patient_creation(valid_patient_payload):
    """Assert valid payload successfully creates PatientCreate model."""
    patient = PatientCreate(**valid_patient_payload)
    assert patient.first_name == "Sarah"
    assert patient.last_name == "Connor"
    assert patient.date_of_birth == date(1985, 5, 14)
    assert patient.sex == SexEnum.FEMALE
    assert patient.phone_number == "5551234567"
    assert patient.emergency_contact_phone == "5559876543"
    assert patient.state == "CA"
    assert patient.zip_code == "90001"


def test_required_fields_only(valid_patient_payload):
    """Assert patient can be registered with only mandatory fields."""
    minimal_payload = {
        "first_name": "James",
        "last_name": "O'Connor",
        "date_of_birth": "1990-10-25",
        "sex": "Male",
        "phone_number": "5552345678",
        "address_line_1": "456 Oak Street",
        "city": "Dallas",
        "state": "tx",
        "zip_code": "75001"
    }
    patient = PatientCreate(**minimal_payload)
    assert patient.first_name == "James"
    assert patient.last_name == "O'Connor"
    assert patient.state == "TX"  # normalized uppercase
    assert patient.preferred_language == "English"  # default
    assert patient.email is None
    assert patient.insurance_provider is None


def test_future_dob_rejected(valid_patient_payload):
    """Assert future date of birth throws a validation error."""
    future_date = (date.today() + timedelta(days=5)).strftime("%m/%d/%Y")
    valid_patient_payload["date_of_birth"] = future_date

    with pytest.raises(ValidationError) as exc_info:
        PatientCreate(**valid_patient_payload)

    errors = exc_info.value.errors()
    assert any("cannot be in the future" in str(e["msg"]) for e in errors)


def test_invalid_dob_format_rejected(valid_patient_payload):
    """Assert malformed date of birth throws an error."""
    valid_patient_payload["date_of_birth"] = "not-a-date"

    with pytest.raises(ValidationError) as exc_info:
        PatientCreate(**valid_patient_payload)

    errors = exc_info.value.errors()
    assert any("Invalid date format" in str(e["msg"]) for e in errors)


def test_invalid_phone_number_length(valid_patient_payload):
    """Assert phone numbers with fewer than 10 digits are rejected."""
    # 3-digit phone number as explicitly mentioned in assessment PDF
    valid_patient_payload["phone_number"] = "555"

    with pytest.raises(ValidationError) as exc_info:
        PatientCreate(**valid_patient_payload)

    errors = exc_info.value.errors()
    assert any("10-digit U.S. phone number" in str(e["msg"]) for e in errors)


def test_phone_number_normalization(valid_patient_payload):
    """Assert varied phone formats (+1, dashes, dots, brackets) are normalized to 10 digits."""
    test_cases = [
        ("+1 (555) 345-6789", "5553456789"),
        ("1-555-345-6789", "5553456789"),
        ("555.345.6789", "5553456789"),
        ("5553456789", "5553456789")
    ]
    for raw_phone, expected_clean in test_cases:
        valid_patient_payload["phone_number"] = raw_phone
        patient = PatientCreate(**valid_patient_payload)
        assert patient.phone_number == expected_clean


def test_invalid_state_rejected(valid_patient_payload):
    """Assert invalid state code is rejected."""
    valid_patient_payload["state"] = "ZZ"

    with pytest.raises(ValidationError) as exc_info:
        PatientCreate(**valid_patient_payload)

    errors = exc_info.value.errors()
    assert any("Invalid U.S. state" in str(e["msg"]) for e in errors)


def test_invalid_zip_code_rejected(valid_patient_payload):
    """Assert invalid zip formats (4 digits, letters) are rejected."""
    invalid_zips = ["1234", "902101", "ABCDE", "9021-"]
    for z in invalid_zips:
        valid_patient_payload["zip_code"] = z
        with pytest.raises(ValidationError):
            PatientCreate(**valid_patient_payload)


def test_valid_zip_plus_four(valid_patient_payload):
    """Assert ZIP+4 format is accepted."""
    valid_patient_payload["zip_code"] = "90210-4321"
    patient = PatientCreate(**valid_patient_payload)
    assert patient.zip_code == "90210-4321"


def test_invalid_name_characters(valid_patient_payload):
    """Assert names with numbers or special characters are rejected."""
    invalid_names = ["Sarah123", "Jane@Doe", "Alex!"]
    for n in invalid_names:
        valid_patient_payload["first_name"] = n
        with pytest.raises(ValidationError):
            PatientCreate(**valid_patient_payload)


def test_valid_name_with_hyphens_and_apostrophes(valid_patient_payload):
    """Assert hyphenated and apostrophe-containing names are allowed."""
    valid_patient_payload["first_name"] = "Mary-Jane"
    valid_patient_payload["last_name"] = "D'Souza"
    patient = PatientCreate(**valid_patient_payload)
    assert patient.first_name == "Mary-Jane"
    assert patient.last_name == "D'Souza"


def test_invalid_sex_enum(valid_patient_payload):
    """Assert unapproved sex options are rejected."""
    valid_patient_payload["sex"] = "NonBinary"  # Must match enum

    with pytest.raises(ValidationError):
        PatientCreate(**valid_patient_payload)


def test_partial_update_validation():
    """Assert partial update schema allows selective field updates while preserving validation."""
    update = PatientUpdate(phone_number="(555) 444-3322", city="San Francisco")
    assert update.phone_number == "5554443322"
    assert update.city == "San Francisco"
    assert update.first_name is None

    # Invalid partial update
    with pytest.raises(ValidationError):
        PatientUpdate(phone_number="123")  # Too short
