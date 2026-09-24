"""
Integration Tests for Voice AI Webhook & Function Calling Tools
Verifies Vapi / Retell / Bland tool call handling, duplicate detection, and error recovery
"""
import pytest
from datetime import date, timedelta


@pytest.fixture
def voice_registration_args():
    return {
        "first_name": "Clara",
        "last_name": "Oswald",
        "date_of_birth": "11/23/1986",
        "sex": "Female",
        "phone_number": "(555) 765-4321",
        "address_line_1": "221B Baker Street",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02108",
        "insurance_provider": "UnitedHealthcare",
        "preferred_language": "English"
    }


def test_get_voice_prompt_and_tool_definitions(client):
    """Test GET /voice/prompt retrieves clinical intake prompt and tool schemas."""
    response = client.get("/voice/prompt")
    assert response.status_code == 200
    data = response.json()
    assert "Alex" in data["prompt"]
    assert "CareCloud" in data["prompt"]
    assert len(data["tools"]) == 4
    tool_names = [t["function"]["name"] for t in data["tools"]]
    assert "check_patient_by_phone" in tool_names
    assert "register_patient" in tool_names
    assert "update_patient" in tool_names
    assert "end_call" in tool_names


def test_voice_duplicate_detection_not_found(client):
    """Test check_patient_by_phone returns found: False for unknown number."""
    payload = {
        "name": "check_patient_by_phone",
        "arguments": {"phone_number": "555-000-1111"}
    }
    response = client.post("/voice/webhook", json=payload)
    assert response.status_code == 200
    res = response.json()["result"]
    assert res["found"] is False


def test_voice_duplicate_detection_found(client, voice_registration_args):
    """Test check_patient_by_phone detects returning patient (Bonus challenge)."""
    # 1. Register Clara
    reg_payload = {
        "name": "register_patient",
        "arguments": voice_registration_args
    }
    reg_res = client.post("/voice/webhook", json=reg_payload)
    assert reg_res.status_code == 200
    assert reg_res.json()["result"]["success"] is True

    # 2. Duplicate check with same phone number
    check_payload = {
        "name": "check_patient_by_phone",
        "arguments": {"phone_number": "(555) 765-4321"}
    }
    check_res = client.post("/voice/webhook", json=check_payload)
    assert check_res.status_code == 200
    res = check_res.json()["result"]
    assert res["found"] is True
    assert res["first_name"] == "Clara"
    assert res["last_name"] == "Oswald"
    assert "Clara Oswald" in res["message"]


def test_voice_register_patient_vapi_format(client, voice_registration_args):
    """Test register_patient tool call wrapped in Vapi-style message.toolCalls envelope."""
    voice_registration_args["first_name"] = "Rory"
    voice_registration_args["last_name"] = "Williams"
    voice_registration_args["phone_number"] = "555-888-9999"

    vapi_payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_12345",
                    "type": "function",
                    "function": {
                        "name": "register_patient",
                        "arguments": voice_registration_args
                    }
                }
            ]
        }
    }

    response = client.post("/voice/webhook", json=vapi_payload)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["toolCallId"] == "call_12345"
    res = results[0]["result"]
    assert res["success"] is True
    assert res["first_name"] == "Rory"
    assert res["last_name"] == "Williams"
    assert res["patient_id"] is not None


def test_voice_register_patient_validation_error_handling(client, voice_registration_args):
    """
    Test that voice webhook returns a clean, speakable validation error message
    when caller provides bad data (e.g. future DOB or short phone), allowing the agent to re-prompt.
    """
    future_dob = (date.today() + timedelta(days=10)).strftime("%m/%d/%Y")
    voice_registration_args["date_of_birth"] = future_dob

    payload = {
        "name": "register_patient",
        "arguments": voice_registration_args
    }

    response = client.post("/voice/webhook", json=payload)
    assert response.status_code == 200
    res = response.json()["result"]
    assert res["success"] is False
    assert res["error_type"] == "validation_error"
    assert "cannot be in the future" in res["message"]


def test_voice_update_patient(client, voice_registration_args):
    """Test update_patient tool call modifying an existing patient's details."""
    # Create patient
    reg_payload = {
        "name": "register_patient",
        "arguments": voice_registration_args
    }
    reg_res = client.post("/voice/webhook", json=reg_payload)
    patient_id = reg_res.json()["result"]["patient_id"]

    # Update patient address
    update_payload = {
        "name": "update_patient",
        "arguments": {
            "patient_id": patient_id,
            "address_line_1": "10 Downing Street",
            "city": "London",
            "state": "FL",
            "zip_code": "33101"
        }
    }

    update_res = client.post("/voice/webhook", json=update_payload)
    assert update_res.status_code == 200
    assert update_res.json()["result"]["success"] is True

    # Verify update via REST API
    get_res = client.get(f"/patients/{patient_id}")
    assert get_res.json()["data"]["address_line_1"] == "10 Downing Street"
    assert get_res.json()["data"]["city"] == "London"
