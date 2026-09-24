"""
Unit and Integration Tests Replicating Real Telephony Call Scenarios
Tests exact payloads, stringified JSON arguments, duplicate lookups, and validation handling.
"""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# The exact demographic data captured during the caller's conversation with Alex:
LIVE_CALL_PAYLOAD_ARGS = {
    "first_name": "Emmett",
    "last_name": "Raza",
    "date_of_birth": "04/25/1989",
    "sex": "Male",
    "phone_number": "0395229280",
    "address_line_1": "Apartment 248, block h, Parachis",
    "city": "Los Angeles",
    "state": "CA",
    "zip_code": "55449",
    "emergency_contact_name": "Alex Bill",
    "emergency_contact_phone": "1234455678"
}


def test_vapi_tool_calls_with_stringified_json_arguments():
    """
    Simulates the exact Vapi tool-calls event where 'arguments' is passed as a stringified JSON string.
    """
    vapi_event = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_live_test_001",
                    "type": "function",
                    "function": {
                        "name": "register_patient",
                        "arguments": json.dumps(LIVE_CALL_PAYLOAD_ARGS)
                    }
                }
            ]
        }
    }

    response = client.post("/voice/webhook", json=vapi_event)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    result_item = data["results"][0]
    assert result_item["toolCallId"] == "call_live_test_001"
    assert result_item["result"]["success"] is True
    assert result_item["result"]["first_name"] == "Emmett"
    assert result_item["result"]["last_name"] == "Raza"
    assert "patient_id" in result_item["result"]


def test_vapi_duplicate_lookup_for_emmett_raza():
    """
    Verifies that check_patient_by_phone detects Emmett Raza by phone 0395229280.
    """
    vapi_event = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_lookup_001",
                    "type": "function",
                    "function": {
                        "name": "check_patient_by_phone",
                        "arguments": json.dumps({"phone_number": "0395229280"})
                    }
                }
            ]
        }
    }

    response = client.post("/voice/webhook", json=vapi_event)
    assert response.status_code == 200
    data = response.json()
    res = data["results"][0]["result"]
    assert res["found"] is True
    assert res["first_name"] == "Emmett"
    assert res["last_name"] == "Raza"


def test_vapi_tool_call_list_alternative_key():
    """
    Tests alternative Vapi payload key 'toolCallList' instead of 'toolCalls'.
    """
    vapi_event = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "call_list_001",
                    "type": "function",
                    "function": {
                        "name": "check_patient_by_phone",
                        "arguments": {"phone_number": "0395229280"}
                    }
                }
            ]
        }
    }

    response = client.post("/voice/webhook", json=vapi_event)
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["result"]["found"] is True


def test_vapi_validation_error_returns_human_friendly_message():
    """
    Verifies that when invalid data (e.g. future DOB) is sent, the API returns
    a speakable validation message instead of crashing.
    """
    bad_args = LIVE_CALL_PAYLOAD_ARGS.copy()
    bad_args["date_of_birth"] = "01/01/2099"  # Future date

    vapi_event = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_bad_dob_001",
                    "type": "function",
                    "function": {
                        "name": "register_patient",
                        "arguments": json.dumps(bad_args)
                    }
                }
            ]
        }
    }

    response = client.post("/voice/webhook", json=vapi_event)
    assert response.status_code == 200
    data = response.json()
    res = data["results"][0]["result"]
    assert res["success"] is False
    assert res["error_type"] == "validation_error"
    assert "future" in res["message"].lower()


def test_vapi_update_patient_details():
    """
    Verifies updating an existing patient record via the update_patient tool call.
    """
    # 1. First retrieve Emmett's ID via search
    search_res = client.get("/patients?phone_number=0395229280")
    patients = search_res.json()["data"]
    assert len(patients) >= 1
    patient_id = patients[0]["patient_id"]

    # 2. Update their address
    vapi_event = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_update_001",
                    "type": "function",
                    "function": {
                        "name": "update_patient",
                        "arguments": json.dumps({
                            "patient_id": patient_id,
                            "address_line_1": "500 Grand Avenue, Suite 10",
                            "city": "Beverly Hills"
                        })
                    }
                }
            ]
        }
    }

    response = client.post("/voice/webhook", json=vapi_event)
    assert response.status_code == 200
    res = response.json()["results"][0]["result"]
    assert res["success"] is True

    # 3. Verify changes persisted
    get_res = client.get(f"/patients/{patient_id}")
    updated_patient = get_res.json()["data"]
    assert updated_patient["address_line_1"] == "500 Grand Avenue, Suite 10"
    assert updated_patient["city"] == "Beverly Hills"
