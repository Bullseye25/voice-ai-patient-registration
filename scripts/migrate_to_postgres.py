"""
CareCloud - SQLite to Supabase / PostgreSQL Data Migration Utility
Copies all existing patient records from local SQLite to Supabase PostgreSQL.
"""
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.patient import Patient, Base

def migrate(sqlite_url: str = "sqlite:///./patients.db", target_url: str = None):
    if not target_url:
        print("[ERROR] Please provide your Supabase/PostgreSQL connection string.")
        print("Usage: python scripts/migrate_to_postgres.py 'postgresql://postgres:pass@db.xxxx.supabase.co:5432/postgres'")
        sys.exit(1)

    print(f"[*] Reading from SQLite: {sqlite_url}")
    sqlite_engine = create_engine(sqlite_url)
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()

    patients = sqlite_session.query(Patient).all()
    print(f"[*] Found {len(patients)} patient record(s) in local SQLite.")

    if not patients:
        print("[*] No records to migrate. Exiting.")
        return

    print(f"[*] Connecting to Target PostgreSQL / Supabase...")
    target_engine = create_engine(target_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=target_engine)
    TargetSession = sessionmaker(bind=target_engine)
    target_session = TargetSession()

    migrated_count = 0
    for p in patients:
        existing = target_session.query(Patient).filter(Patient.patient_id == p.patient_id).first()
        if existing:
            print(f"    - Skipping already existing patient: {p.first_name} {p.last_name} ({p.patient_id})")
            continue

        new_p = Patient(
            patient_id=p.patient_id,
            first_name=p.first_name,
            last_name=p.last_name,
            date_of_birth=p.date_of_birth,
            sex=p.sex,
            phone_number=p.phone_number,
            email=p.email,
            address_line_1=p.address_line_1,
            address_line_2=p.address_line_2,
            city=p.city,
            state=p.state,
            zip_code=p.zip_code,
            insurance_provider=p.insurance_provider,
            insurance_member_id=p.insurance_member_id,
            preferred_language=p.preferred_language,
            emergency_contact_name=p.emergency_contact_name,
            emergency_contact_phone=p.emergency_contact_phone,
            created_at=p.created_at,
            updated_at=p.updated_at,
            deleted_at=p.deleted_at
        )
        target_session.add(new_p)
        migrated_count += 1

    target_session.commit()
    print(f"[SUCCESS] Successfully migrated {migrated_count} patient(s) to Supabase PostgreSQL!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_db_url = sys.argv[1]
    else:
        target_db_url = os.getenv("DATABASE_URL")
        if target_db_url and target_db_url.startswith("sqlite"):
            target_db_url = None

    migrate(target_url=target_db_url)
