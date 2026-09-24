"""
Patient Pydantic Validation Schemas & API Envelopes
Enforces U.S. Healthcare Patient Demographic Standards
"""
import re
from datetime import date, datetime
from typing import Optional, List, Generic, TypeVar, Any
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    EmailStr,
    ConfigDict
)
from app.models.patient import SexEnum

# Valid 2-letter U.S. State and Territory Abbreviations
VALID_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "VI", "GU", "AS", "MP"
}

NAME_REGEX = re.compile(r"^[A-Za-z\s'\-]+$")
ZIP_REGEX = re.compile(r"^\d{5}(-\d{4})?$")


def normalize_phone(v: Optional[str]) -> Optional[str]:
    """Cleans phone numbers and verifies exactly 10 digits."""
    if v is None:
        return None
    # Strip all non-digit characters
    digits = re.sub(r"\D", "", v)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError(
            f"Invalid phone number: must be a 10-digit U.S. phone number. Received {len(digits)} digits."
        )
    return digits


def parse_and_validate_dob(v: Any) -> date:
    """Parses date string or date object and asserts it is in the past."""
    parsed_date = None
    if isinstance(v, date):
        parsed_date = v
    elif isinstance(v, str):
        v = v.strip()
        # Accept MM/DD/YYYY, MM-DD-YYYY, or YYYY-MM-DD
        date_formats = ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"]
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(v, fmt).date()
                break
            except ValueError:
                continue
        if not parsed_date:
            raise ValueError(
                "Invalid date format for date_of_birth. Expected MM/DD/YYYY (e.g. 05/14/1985)."
            )
    else:
        raise ValueError("date_of_birth must be a valid date or date string (MM/DD/YYYY).")

    if parsed_date > date.today():
        raise ValueError("date_of_birth cannot be in the future.")

    # Practical validation: patient cannot be older than 130 years
    if (date.today().year - parsed_date.year) > 130:
        raise ValueError("date_of_birth is invalid: year is outside reasonable range.")

    return parsed_date


class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50, description="1–50 chars, alphabetic + hyphens/apostrophes")
    last_name: str = Field(..., min_length=1, max_length=50, description="1–50 chars, alphabetic + hyphens/apostrophes")
    date_of_birth: date = Field(..., description="Valid date, not in future, MM/DD/YYYY")
    sex: SexEnum = Field(..., description="Male, Female, Other, Decline to Answer")
    phone_number: str = Field(..., description="Valid U.S. 10-digit phone number")
    email: Optional[EmailStr] = Field(None, description="Valid email format")
    address_line_1: str = Field(..., min_length=1, max_length=255, description="Street address")
    address_line_2: Optional[str] = Field(None, max_length=255, description="Apt/Suite/Unit")
    city: str = Field(..., min_length=1, max_length=100, description="City name")
    state: str = Field(..., min_length=2, max_length=2, description="Valid 2-letter U.S. state abbreviation")
    zip_code: str = Field(..., description="5-digit or ZIP+4 U.S. format")
    insurance_provider: Optional[str] = Field(None, max_length=100)
    insurance_member_id: Optional[str] = Field(None, max_length=50)
    preferred_language: Optional[str] = Field("English", max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty or blank spaces.")
        if not NAME_REGEX.match(v):
            raise ValueError(
                "Name may only contain alphabetic characters, spaces, hyphens, and apostrophes."
            )
        return v

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_dob(cls, v: Any) -> date:
        return parse_and_validate_dob(v)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        return normalize_phone(v)

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        upper_v = v.strip().upper()
        if upper_v not in VALID_US_STATES:
            raise ValueError(
                f"Invalid U.S. state '{v}'. Must be a valid 2-letter state code (e.g. CA, NY, TX)."
            )
        return upper_v

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, v: str) -> str:
        v = v.strip()
        if not ZIP_REGEX.match(v):
            raise ValueError(
                f"Invalid U.S. zip code '{v}'. Must be 5 digits (e.g. 90210) or ZIP+4 (e.g. 90210-1234)."
            )
        return v

    @field_validator("address_line_1", "city")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace.")
        return v


class PatientCreate(PatientBase):
    """Schema used when creating a new patient record."""
    pass


class PatientUpdate(BaseModel):
    """Schema used when updating an existing patient record (supports partial updates)."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    date_of_birth: Optional[Any] = Field(None)
    sex: Optional[SexEnum] = Field(None)
    phone_number: Optional[str] = Field(None)
    email: Optional[EmailStr] = Field(None)
    address_line_1: Optional[str] = Field(None, min_length=1, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None)
    insurance_provider: Optional[str] = Field(None, max_length=100)
    insurance_member_id: Optional[str] = Field(None, max_length=50)
    preferred_language: Optional[str] = Field(None, max_length=50)
    emergency_contact_name: Optional[str] = Field(None, max_length=100)
    emergency_contact_phone: Optional[str] = Field(None)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank.")
        if not NAME_REGEX.match(v):
            raise ValueError("Name may only contain alphabetic characters, spaces, hyphens, and apostrophes.")
        return v

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_dob(cls, v: Any) -> Optional[date]:
        if v is None:
            return None
        return parse_and_validate_dob(v)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return normalize_phone(v)

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        return normalize_phone(v)

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        upper_v = v.strip().upper()
        if upper_v not in VALID_US_STATES:
            raise ValueError(f"Invalid U.S. state '{v}'. Must be a valid 2-letter state code.")
        return upper_v

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not ZIP_REGEX.match(v):
            raise ValueError(f"Invalid U.S. zip code '{v}'. Must be 5 digits or ZIP+4.")
        return v


class PatientResponse(PatientBase):
    patient_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Standard Response Envelopes
T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None


class StandardEnvelope(BaseModel, Generic[T]):
    data: Optional[T] = None
    error: Optional[ErrorBody] = None


class ErrorEnvelope(BaseModel):
    data: Optional[Any] = None
    error: ErrorBody
