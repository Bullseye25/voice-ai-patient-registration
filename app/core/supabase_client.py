"""
Supabase Official Python SDK Client Integration
Provides cloud database operations and synchronization via supabase-py.
"""
from typing import Optional, List, Dict, Any
import os
from supabase import create_client, Client
from app.config import settings

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Returns singleton instance of the official Supabase Client."""
    global _supabase_client
    if _supabase_client is None:
        url = settings.SUPABASE_URL or os.getenv("SUPABASE_URL")
        key = settings.SUPABASE_KEY or os.getenv("SUPABASE_KEY")
        if url and key:
            try:
                _supabase_client = create_client(url, key)
            except Exception as e:
                print(f"[WARNING] Could not initialize Supabase SDK client: {e}")
                return None
    return _supabase_client


def is_supabase_enabled() -> bool:
    """Checks if Supabase credentials are configured."""
    return bool((settings.SUPABASE_URL or os.getenv("SUPABASE_URL")) and 
                (settings.SUPABASE_KEY or os.getenv("SUPABASE_KEY")))


def sync_patient_to_supabase(patient_dict: dict) -> bool:
    """
    Upserts a patient record to Supabase Cloud using the official Supabase SDK.
    Returns True if successfully synchronized.
    """
    if os.getenv("TESTING") == "true":
        return True

    client = get_supabase_client()
    if not client:
        return False

    try:
        # Convert date and datetime objects to ISO strings if needed
        data = {}
        for k, v in patient_dict.items():
            if hasattr(v, "isoformat"):
                data[k] = v.isoformat()
            else:
                data[k] = v

        client.table("patients").upsert(data, on_conflict="patient_id").execute()
        return True
    except Exception as e:
        # If table doesn't exist yet in Supabase, log notice gracefully
        print(f"[SUPABASE SDK SYNC NOTICE] {e}")
        return False


def delete_patient_from_supabase(patient_id: str) -> bool:
    """Permanently deletes a patient from Supabase Cloud."""
    if os.getenv("TESTING") == "true":
        return True

    client = get_supabase_client()
    if not client:
        return False

    try:
        client.table("patients").delete().eq("patient_id", patient_id).execute()
        return True
    except Exception as e:
        print(f"[SUPABASE DELETE NOTICE] {e}")
        return False


import time
from datetime import date, datetime, timezone

_last_reconcile_time: float = 0.0


def reconcile_patients_with_supabase(db, force: bool = False) -> bool:
    """
    Bidirectionally reconciles local SQLite with Supabase Cloud:
    1. If a patient was permanently deleted from Supabase directly, deletes it from SQLite.
    2. If a patient exists in Supabase, upserts it into local SQLite (ensuring deleted_at,
       updates, and new registrations are fully mirrored).
    3. Uses a 3-second debounce cooldown unless force=True.
    """
    global _last_reconcile_time

    if os.getenv("TESTING") == "true":
        return False

    if not is_supabase_enabled():
        return False

    client = get_supabase_client()
    if not client:
        return False

    now = time.time()
    if not force and (now - _last_reconcile_time < 3.0):
        return True

    try:
        from app.models.patient import Patient, SexEnum

        res = client.table("patients").select("*").execute()
        if res.data is None:
            return False

        remote_rows = res.data
        remote_ids = {row["patient_id"] for row in remote_rows if "patient_id" in row}

        # 1. Remove local records that were permanently purged in Supabase
        local_patients = db.query(Patient).all()
        for lp in local_patients:
            if lp.patient_id not in remote_ids:
                db.delete(lp)

        # 2. Upsert/sync all active & soft-deleted records from Supabase
        for row in remote_rows:
            pid = row.get("patient_id")
            if not pid:
                continue

            # Safe DOB parse
            dob_raw = row.get("date_of_birth")
            dob_val = None
            if dob_raw:
                try:
                    dob_val = date.fromisoformat(str(dob_raw)[:10])
                except Exception:
                    dob_val = date(2000, 1, 1)

            # Safe Datetime parse
            def parse_dt(raw):
                if not raw:
                    return None
                try:
                    return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                except Exception:
                    return datetime.now(timezone.utc)

            del_val = parse_dt(row.get("deleted_at"))
            created_val = parse_dt(row.get("created_at"))
            updated_val = parse_dt(row.get("updated_at"))

            # Safe SexEnum
            sex_raw = row.get("sex", "Other")
            try:
                sex_val = SexEnum(sex_raw)
            except Exception:
                sex_val = SexEnum.OTHER

            local_p = db.query(Patient).filter(Patient.patient_id == pid).first()
            if local_p:
                local_p.first_name = row.get("first_name", local_p.first_name)
                local_p.last_name = row.get("last_name", local_p.last_name)
                if dob_val:
                    local_p.date_of_birth = dob_val
                local_p.sex = sex_val
                local_p.phone_number = row.get("phone_number", local_p.phone_number)
                local_p.email = row.get("email", local_p.email)
                local_p.address_line_1 = row.get("address_line_1", local_p.address_line_1)
                local_p.address_line_2 = row.get("address_line_2", local_p.address_line_2)
                local_p.city = row.get("city", local_p.city)
                local_p.state = row.get("state", local_p.state)
                local_p.zip_code = row.get("zip_code", local_p.zip_code)
                local_p.insurance_provider = row.get("insurance_provider", local_p.insurance_provider)
                local_p.insurance_member_id = row.get("insurance_member_id", local_p.insurance_member_id)
                local_p.preferred_language = row.get("preferred_language", local_p.preferred_language)
                local_p.emergency_contact_name = row.get("emergency_contact_name", local_p.emergency_contact_name)
                local_p.emergency_contact_phone = row.get("emergency_contact_phone", local_p.emergency_contact_phone)
                local_p.deleted_at = del_val
                if updated_val:
                    local_p.updated_at = updated_val
            else:
                new_p = Patient(
                    patient_id=pid,
                    first_name=row.get("first_name", "Unknown"),
                    last_name=row.get("last_name", "Unknown"),
                    date_of_birth=dob_val or date(2000, 1, 1),
                    sex=sex_val,
                    phone_number=row.get("phone_number", "0000000000"),
                    email=row.get("email"),
                    address_line_1=row.get("address_line_1", "Unknown"),
                    address_line_2=row.get("address_line_2"),
                    city=row.get("city", "Unknown"),
                    state=row.get("state", "US"),
                    zip_code=row.get("zip_code", "00000"),
                    insurance_provider=row.get("insurance_provider"),
                    insurance_member_id=row.get("insurance_member_id"),
                    preferred_language=row.get("preferred_language") or "English",
                    emergency_contact_name=row.get("emergency_contact_name"),
                    emergency_contact_phone=row.get("emergency_contact_phone"),
                    deleted_at=del_val,
                    created_at=created_val or datetime.now(timezone.utc),
                    updated_at=updated_val or datetime.now(timezone.utc)
                )
                db.add(new_p)

        db.commit()
        _last_reconcile_time = time.time()
        return True
    except Exception as e:
        print(f"[SUPABASE RECONCILIATION NOTICE] {e}")
        db.rollback()
        return False

