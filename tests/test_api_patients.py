"""
Integration Tests for Patient REST API
Verifies Endpoints, Envelopes, HTTP Status Codes, Query Filters, Soft Deletes, and Persistence
"""
import pytest
from datetime import date, timedelta


@pytest.fixture
def sample_patient_dict():
    return {
        "first_name": "Alexander",
        "last_name": "Hamilton",
        "date_of_birth": "01/11/1980",
        "sex": "Male",
        "phone_number": "555-555-1234",
        "email": "alex.hamilton@example.com",
        "address_line_1": "55 Wall Street",
        "address_line_2": "Apt 10A",
        "city": "New York",
        "state": "NY",
        "zip_code": "10005",
        "insurance_provider": "Aetna",
        "insurance_member_id": "AET-123456",
        "preferred_language": "English",
        "emergency_contact_name": "Elizabeth Hamilton",
        "emergency_contact_phone": "555-555-4321"
    }


def test_health_check(client):
    """Test health probe endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_patient_success(client, sample_patient_dict):
    """Test POST /patients creates a new record and returns 201 with standard envelope."""
    response = client.post("/patients", json=sample_patient_dict)
    assert response.status_code == 201
    res_data = response.json()

    assert res_data["error"] is None
    data = res_data["data"]
    assert data["first_name"] == "Alexander"
    assert data["last_name"] == "Hamilton"
    assert data["phone_number"] == "5555551234"  # Normalized
    assert data["patient_id"] is not None
    assert len(data["patient_id"]) == 36  # UUID length
    assert data["created_at"] is not None
    assert data["deleted_at"] is None


def test_create_patient_future_dob_validation_error(client, sample_patient_dict):
    """Test POST /patients rejects future date of birth with 422 and structured error envelope."""
    future_date = (date.today() + timedelta(days=30)).strftime("%m/%d/%Y")
    sample_patient_dict["date_of_birth"] = future_date

    response = client.post("/patients", json=sample_patient_dict)
    assert response.status_code == 422
    res_data = response.json()

    assert res_data["data"] is None
    assert res_data["error"]["code"] == "VALIDATION_ERROR"
    assert any("cannot be in the future" in d["message"] for d in res_data["error"]["details"])


def test_create_patient_short_phone_validation_error(client, sample_patient_dict):
    """Test POST /patients rejects 3-digit phone numbers with 422."""
    sample_patient_dict["phone_number"] = "555"

    response = client.post("/patients", json=sample_patient_dict)
    assert response.status_code == 422
    res_data = response.json()

    assert res_data["data"] is None
    assert res_data["error"]["code"] == "VALIDATION_ERROR"
    assert any("10-digit U.S. phone number" in d["message"] for d in res_data["error"]["details"])


def test_get_patient_by_id(client, sample_patient_dict):
    """Test GET /patients/:id retrieves active patient record."""
    create_res = client.post("/patients", json=sample_patient_dict)
    patient_id = create_res.json()["data"]["patient_id"]

    get_res = client.get(f"/patients/{patient_id}")
    assert get_res.status_code == 200
    res_data = get_res.json()

    assert res_data["error"] is None
    assert res_data["data"]["patient_id"] == patient_id
    assert res_data["data"]["first_name"] == "Alexander"


def test_get_patient_not_found(client):
    """Test GET /patients/:id returns 404 with error envelope when not found."""
    response = client.get("/patients/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    res_data = response.json()

    assert res_data["data"] is None
    assert res_data["error"]["code"] == "NOT_FOUND"
    assert "not found" in res_data["error"]["message"].lower()


def test_list_patients_and_query_filters(client, sample_patient_dict):
    """Test GET /patients with query parameters ?last_name=, ?date_of_birth=, ?phone_number="""
    # Create patient 1: Alexander Hamilton (5555551234, DOB: 01/11/1980)
    client.post("/patients", json=sample_patient_dict)

    # Create patient 2: Thomas Jefferson (5556667777, DOB: 04/13/1985)
    patient_2 = sample_patient_dict.copy()
    patient_2["first_name"] = "Thomas"
    patient_2["last_name"] = "Jefferson"
    patient_2["phone_number"] = "555-666-7777"
    patient_2["date_of_birth"] = "04/13/1985"
    client.post("/patients", json=patient_2)

    # 1. List all active
    all_res = client.get("/patients")
    assert all_res.status_code == 200
    assert len(all_res.json()["data"]) == 2

    # 2. Filter by last_name
    name_res = client.get("/patients?last_name=Jefferson")
    assert len(name_res.json()["data"]) == 1
    assert name_res.json()["data"][0]["first_name"] == "Thomas"

    # 3. Filter by phone_number
    phone_res = client.get("/patients?phone_number=(555) 555-1234")
    assert len(phone_res.json()["data"]) == 1
    assert phone_res.json()["data"][0]["first_name"] == "Alexander"

    # 4. Filter by date_of_birth
    dob_res = client.get("/patients?date_of_birth=04/13/1985")
    assert len(dob_res.json()["data"]) == 1
    assert dob_res.json()["data"][0]["first_name"] == "Thomas"

    # 5. Invalid date_of_birth filter returns 400
    bad_dob_res = client.get("/patients?date_of_birth=invalid-date")
    assert bad_dob_res.status_code == 400
    assert bad_dob_res.json()["error"]["code"] == "BAD_REQUEST"


def test_put_patient_partial_update(client, sample_patient_dict):
    """Test PUT /patients/:id supports partial updates."""
    create_res = client.post("/patients", json=sample_patient_dict)
    patient_id = create_res.json()["data"]["patient_id"]

    # Partially update phone and city only
    update_payload = {
        "phone_number": "(555) 999-8877",
        "city": "Brooklyn"
    }

    put_res = client.put(f"/patients/{patient_id}", json=update_payload)
    assert put_res.status_code == 200
    data = put_res.json()["data"]

    assert data["phone_number"] == "5559998877"
    assert data["city"] == "Brooklyn"
    # Preserves other existing fields
    assert data["first_name"] == "Alexander"
    assert data["last_name"] == "Hamilton"
    assert data["state"] == "NY"


def test_soft_delete_patient(client, sample_patient_dict):
    """Test DELETE /patients/:id soft-deletes record (does not hard-delete)."""
    create_res = client.post("/patients", json=sample_patient_dict)
    patient_id = create_res.json()["data"]["patient_id"]

    # Delete patient
    del_res = client.delete(f"/patients/{patient_id}")
    assert del_res.status_code == 200
    assert del_res.json()["data"]["patient_id"] == patient_id
    assert del_res.json()["data"]["deleted_at"] is not None

    # Subsequent GET /patients/:id must return 404
    get_res = client.get(f"/patients/{patient_id}")
    assert get_res.status_code == 404

    # GET /patients list must not include the soft-deleted patient
    list_res = client.get("/patients")
    ids = [p["patient_id"] for p in list_res.json()["data"]]
    assert patient_id not in ids


def test_persistence_across_server_restarts(tmp_path, sample_patient_dict):
    """
    Test SQLite disk persistence: verifies data created survives across session and engine rebuilds.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    from app.services.patient_service import PatientService
    from app.schemas.patient import PatientCreate

    db_file = tmp_path / "persistent_test.db"
    db_url = f"sqlite:///{db_file}"

    # Session 1: Create table and save patient
    engine1 = create_engine(db_url)
    Base.metadata.create_all(bind=engine1)
    Session1 = sessionmaker(bind=engine1)
    db1 = Session1()

    patient_in = PatientCreate(**sample_patient_dict)
    saved_patient = PatientService.create_patient(db1, patient_in)
    saved_id = saved_patient.patient_id
    db1.close()
    engine1.dispose()  # Simulate complete server shutdown

    # Session 2: Fresh engine on same DB file (simulating server restart)
    engine2 = create_engine(db_url)
    Session2 = sessionmaker(bind=engine2)
    db2 = Session2()

    retrieved_patient = PatientService.get_patient_by_id(db2, saved_id)
    assert retrieved_patient is not None
    assert retrieved_patient.patient_id == saved_id
    assert retrieved_patient.first_name == "Alexander"
    assert retrieved_patient.last_name == "Hamilton"
    assert retrieved_patient.phone_number == "5555551234"
    db2.close()
    engine2.dispose()


def test_export_patients_csv(client, sample_patient_dict):
    """Test GET /patients/export/csv exports valid CSV content with headers and patient data."""
    client.post("/patients", json=sample_patient_dict)

    res = client.get("/patients/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert 'attachment; filename="carecloud_patients.csv"' in res.headers.get("content-disposition", "")

    csv_text = res.text
    assert "patient_id,first_name,last_name" in csv_text
    assert "Alexander,Hamilton" in csv_text
    assert "United States" in csv_text

