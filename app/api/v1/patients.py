"""
Patient REST API Endpoints
Implements CRUD, query filtering, soft deletion, and unified JSON response envelopes.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.patient_service import PatientService
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    StandardEnvelope,
    parse_and_validate_dob
)

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardEnvelope[PatientResponse],
    summary="Create a new patient record"
)
def create_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db)
):
    """
    Registers a new patient with rigorous server-side validation.
    Returns the created record containing the generated UUID patient_id.
    """
    patient = PatientService.create_patient(db, patient_in)
    return StandardEnvelope(data=patient.to_dict(), error=None)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=StandardEnvelope[List[PatientResponse]],
    summary="List patients with optional filtering"
)
def list_patients(
    last_name: Optional[str] = Query(None, description="Filter by patient last name"),
    date_of_birth: Optional[str] = Query(None, description="Filter by birth date (MM/DD/YYYY or YYYY-MM-DD)"),
    phone_number: Optional[str] = Query(None, description="Filter by phone number"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List all active patients. Supports query filters:
    - ?last_name=
    - ?date_of_birth=
    - ?phone_number=
    Excludes soft-deleted patient records.
    """
    parsed_dob = None
    if date_of_birth:
        try:
            parsed_dob = parse_and_validate_dob(date_of_birth)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date_of_birth query parameter: {str(e)}"
            )

    patients = PatientService.list_patients(
        db,
        last_name=last_name,
        date_of_birth=parsed_dob,
        phone_number=phone_number,
        skip=skip,
        limit=limit
    )
    return StandardEnvelope(data=[p.to_dict() for p in patients], error=None)


@router.get(
    "/{patient_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardEnvelope[PatientResponse],
    summary="Retrieve single patient by UUID"
)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve single active patient record by patient_id (UUID).
    Returns 404 if the patient does not exist or has been soft-deleted.
    """
    patient = PatientService.get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID '{patient_id}' not found."
        )
    return StandardEnvelope(data=patient.to_dict(), error=None)


@router.put(
    "/{patient_id}",
    status_code=status.HTTP_200_OK,
    response_model=StandardEnvelope[PatientResponse],
    summary="Update patient record (partial updates supported)"
)
def update_patient(
    patient_id: str,
    update_in: PatientUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates an existing patient record. Supports partial updates.
    Returns 404 if patient is not found or has been soft-deleted.
    """
    updated_patient = PatientService.update_patient(db, patient_id, update_in)
    if not updated_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID '{patient_id}' not found."
        )
    return StandardEnvelope(data=updated_patient.to_dict(), error=None)


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete patient record"
)
def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db)
):
    """
    Soft-deletes a patient record by setting deleted_at timestamp.
    Does not hard-delete from the database.
    """
    patient = PatientService.soft_delete_patient(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID '{patient_id}' not found."
        )
    return StandardEnvelope(
        data={
            "patient_id": patient.patient_id,
            "message": "Patient record soft-deleted successfully.",
            "deleted_at": patient.deleted_at.isoformat() if patient.deleted_at else None
        },
        error=None
    )
