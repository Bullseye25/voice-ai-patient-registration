"""
Patient Service Layer
Handles business operations, persistence queries, filtering, and soft deletions.
"""
import json
import os
from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.patient import Patient, SexEnum
from app.schemas.patient import PatientCreate, PatientUpdate, parse_and_validate_dob, normalize_phone
from app.core.supabase_client import (
    sync_patient_to_supabase,
    delete_patient_from_supabase,
    reconcile_patients_with_supabase
)


class PatientService:

    @staticmethod
    def sync_with_supabase(db: Session, force: bool = True) -> bool:
        """Forces an immediate bidirectional synchronization with Supabase Cloud."""
        return reconcile_patients_with_supabase(db, force=force)

    @staticmethod
    def create_patient(db: Session, patient_in: PatientCreate) -> Patient:
        """Creates and persists a new patient record."""
        patient = Patient(
            first_name=patient_in.first_name,
            last_name=patient_in.last_name,
            date_of_birth=patient_in.date_of_birth,
            sex=patient_in.sex,
            phone_number=patient_in.phone_number,
            email=patient_in.email,
            address_line_1=patient_in.address_line_1,
            address_line_2=patient_in.address_line_2,
            city=patient_in.city,
            state=patient_in.state,
            zip_code=patient_in.zip_code,
            insurance_provider=patient_in.insurance_provider,
            insurance_member_id=patient_in.insurance_member_id,
            preferred_language=patient_in.preferred_language or "English",
            emergency_contact_name=patient_in.emergency_contact_name,
            emergency_contact_phone=patient_in.emergency_contact_phone
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        sync_patient_to_supabase(patient.to_dict())
        return patient

    @staticmethod
    def get_patient_by_id(
        db: Session,
        patient_id: str,
        include_deleted: bool = False
    ) -> Optional[Patient]:
        """Retrieves a single patient by UUID, excluding soft-deleted records by default."""
        query = db.query(Patient).filter(Patient.patient_id == patient_id)
        if not include_deleted:
            query = query.filter(Patient.deleted_at.is_(None))
        patient = query.first()
        if not patient:
            # Check if recently updated in Supabase
            if reconcile_patients_with_supabase(db, force=True):
                query = db.query(Patient).filter(Patient.patient_id == patient_id)
                if not include_deleted:
                    query = query.filter(Patient.deleted_at.is_(None))
                patient = query.first()
        return patient

    @staticmethod
    def find_by_phone(
        db: Session,
        phone_number: str,
        include_deleted: bool = False
    ) -> Optional[Patient]:
        """Finds patient by normalized phone number (used for duplicate detection)."""
        clean_phone = normalize_phone(phone_number)
        query = db.query(Patient).filter(Patient.phone_number == clean_phone)
        if not include_deleted:
            query = query.filter(Patient.deleted_at.is_(None))
        return query.first()

    @staticmethod
    def list_patients(
        db: Session,
        last_name: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        phone_number: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[Patient]:
        """
        Lists active patients with optional query filtering by last_name, date_of_birth, or phone_number.
        Automatically reconciles with Supabase Cloud if enabled so deletions and updates in Supabase
        are immediately reflected locally.
        """
        # Reconcile local SQLite with Supabase Cloud
        reconcile_patients_with_supabase(db)

        query = db.query(Patient)

        if not include_deleted:
            query = query.filter(Patient.deleted_at.is_(None))

        if last_name:
            query = query.filter(Patient.last_name.ilike(f"%{last_name.strip()}%"))

        if date_of_birth:
            query = query.filter(Patient.date_of_birth == date_of_birth)

        if phone_number:
            try:
                clean_phone = normalize_phone(phone_number)
                query = query.filter(Patient.phone_number == clean_phone)
            except ValueError:
                # If invalid phone is searched, match exact substring
                query = query.filter(Patient.phone_number.like(f"%{phone_number.strip()}%"))

        return query.order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_patient(
        db: Session,
        patient_id: str,
        update_in: PatientUpdate
    ) -> Optional[Patient]:
        """
        Updates an existing patient record. Supports partial updates.
        """
        patient = db.query(Patient).filter(
            and_(Patient.patient_id == patient_id, Patient.deleted_at.is_(None))
        ).first()

        if not patient:
            return None

        update_data = update_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(patient, field, value)

        patient.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(patient)
        sync_patient_to_supabase(patient.to_dict())
        return patient

    @staticmethod
    def soft_delete_patient(db: Session, patient_id: str) -> Optional[Patient]:
        """
        Soft-deletes a patient record by populating deleted_at timestamp.
        Does not hard-delete.
        """
        patient = db.query(Patient).filter(
            and_(Patient.patient_id == patient_id, Patient.deleted_at.is_(None))
        ).first()

        if not patient:
            return None

        patient.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(patient)
        sync_patient_to_supabase(patient.to_dict())
        return patient

    @staticmethod
    def restore_patient(db: Session, patient_id: str) -> Optional[Patient]:
        """
        Restores an archived patient record by clearing deleted_at timestamp.
        """
        patient = db.query(Patient).filter(
            and_(Patient.patient_id == patient_id, Patient.deleted_at.is_not(None))
        ).first()

        if not patient:
            return None

        patient.deleted_at = None
        patient.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(patient)
        sync_patient_to_supabase(patient.to_dict())
        return patient

    @staticmethod
    def hard_delete_patient(db: Session, patient_id: str) -> bool:
        """
        Permanently purges a patient record from both local SQLite and Supabase Cloud.
        """
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            return False

        db.delete(patient)
        db.commit()
        delete_patient_from_supabase(patient_id)
        return True

    @staticmethod
    def seed_demo_data_if_empty(db: Session, seed_file_path: str = "seed/patients_seed.json"):
        """Seeds initial patient records if database is empty."""
        try:
            count = db.query(Patient).count()
            if count == 0 and os.path.exists(seed_file_path):
                with open(seed_file_path, "r", encoding="utf-8") as f:
                    seed_data = json.load(f)
                for item in seed_data:
                    patient_create = PatientCreate(**item)
                    PatientService.create_patient(db, patient_create)
        except Exception:
            db.rollback()
