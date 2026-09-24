"""
Voice AI Agent Telephony Webhooks & Function Calling Handlers
Supports Vapi, Retell, Bland.ai, and generic HTTP tool calls.
"""
import logging
import os
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.core.database import get_db
from app.services.patient_service import PatientService
from app.schemas.patient import PatientCreate, PatientUpdate
from app.schemas.voice import VoiceWebhookResponse, ToolCallResult

logger = logging.getLogger("VoiceWebhook")
router = APIRouter(prefix="/voice", tags=["Voice AI Agent"])


def execute_tool(name: str, args: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Dispatches tool calls to the appropriate business logic handler."""
    logger.info(f"Executing Voice AI tool call: '{name}' with args: {args}")

    if name == "check_patient_by_phone":
        phone = args.get("phone_number", "")
        patient = PatientService.find_by_phone(db, phone)
        if patient:
            return {
                "found": True,
                "patient_id": patient.patient_id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "message": f"Existing record found for {patient.first_name} {patient.last_name}."
            }
        return {
            "found": False,
            "message": "No existing record found for this phone number."
        }

    elif name == "register_patient":
        try:
            patient_in = PatientCreate(**args)
            patient = PatientService.create_patient(db, patient_in)
            logger.info(f"Voice Agent successfully registered patient: {patient.patient_id}")
            return {
                "success": True,
                "patient_id": patient.patient_id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "message": f"Successfully registered {patient.first_name} {patient.last_name}."
            }
        except ValidationError as e:
            errors = [f"{err.get('loc', [''])[0]}: {err.get('msg')}" for err in e.errors()]
            error_summary = "; ".join(errors)
            logger.warning(f"Voice Agent registration validation failed: {error_summary}")
            return {
                "success": False,
                "error_type": "validation_error",
                "message": f"Data validation failed: {error_summary}. Please ask the caller to clarify."
            }
        except Exception as e:
            logger.error(f"Error during voice registration write: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error_type": "database_error",
                "message": "A database error occurred while saving the record."
            }

    elif name == "update_patient":
        patient_id = args.get("patient_id")
        if not patient_id:
            return {"success": False, "message": "Missing patient_id for update."}
        try:
            update_data = {k: v for k, v in args.items() if k != "patient_id"}
            patient_update = PatientUpdate(**update_data)
            patient = PatientService.update_patient(db, patient_id, patient_update)
            if not patient:
                return {"success": False, "message": f"Patient with ID {patient_id} not found."}
            return {
                "success": True,
                "patient_id": patient.patient_id,
                "message": "Patient record updated successfully."
            }
        except ValidationError as e:
            errors = [f"{err.get('loc', [''])[0]}: {err.get('msg')}" for err in e.errors()]
            return {"success": False, "message": f"Validation error: {'; '.join(errors)}"}

    return {
        "success": False,
        "message": f"Unknown tool name: {name}"
    }


@router.post("/webhook", status_code=status.HTTP_200_OK, summary="Voice Agent Tool Webhook")
async def voice_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receives tool-call events from voice platforms (Vapi, Retell, Bland.ai)
    and executes patient registration or duplicate lookups.
    """
    payload = await request.json()
    logger.info(f"Incoming Voice Webhook payload: {payload}")

    # Case 1: Vapi-style message wrapper
    if "message" in payload and "toolCalls" in payload["message"]:
        results = []
        for call in payload["message"]["toolCalls"]:
            tool_id = call.get("id")
            func = call.get("function", {})
            name = func.get("name")
            args = func.get("arguments", {})
            # If arguments is passed as JSON string
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            res = execute_tool(name, args, db)
            results.append({"toolCallId": tool_id, "result": res})
        return {"results": results}

    # Case 2: Retell / Bland / direct tool-call format
    if "name" in payload and "arguments" in payload:
        name = payload["name"]
        args = payload["arguments"]
        res = execute_tool(name, args, db)
        return {"result": res}

    # Case 3: Direct function call at root
    if "function" in payload:
        func = payload["function"]
        res = execute_tool(func.get("name"), func.get("arguments", {}), db)
        return {"result": res}

    return {"message": "Webhook received but no actionable tool calls found."}


@router.get("/prompt", status_code=status.HTTP_200_OK, summary="Get Intake Coordinator System Prompt")
def get_system_prompt():
    """Returns the full clinical intake system prompt and tool definitions."""
    prompt_file = "prompts/patient_intake_prompt.md"
    content = ""
    if os.path.exists(prompt_file):
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()

    tools = [
        {
            "type": "function",
            "function": {
                "name": "check_patient_by_phone",
                "description": "Check if an existing patient record exists by phone number (duplicate detection).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone_number": {"type": "string", "description": "10-digit U.S. phone number"}
                    },
                    "required": ["phone_number"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "register_patient",
                "description": "Create and persist a new patient record upon caller confirmation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "date_of_birth": {"type": "string", "description": "MM/DD/YYYY format, past date only"},
                        "sex": {"type": "string", "enum": ["Male", "Female", "Other", "Decline to Answer"]},
                        "phone_number": {"type": "string", "description": "10-digit U.S. phone number"},
                        "address_line_1": {"type": "string"},
                        "address_line_2": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string", "description": "2-letter state code"},
                        "zip_code": {"type": "string", "description": "5-digit zip"},
                        "email": {"type": "string"},
                        "insurance_provider": {"type": "string"},
                        "insurance_member_id": {"type": "string"},
                        "preferred_language": {"type": "string"},
                        "emergency_contact_name": {"type": "string"},
                        "emergency_contact_phone": {"type": "string"}
                    },
                    "required": [
                        "first_name", "last_name", "date_of_birth", "sex",
                        "phone_number", "address_line_1", "city", "state", "zip_code"
                    ]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_patient",
                "description": "Update an existing patient record.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"},
                        "phone_number": {"type": "string"},
                        "address_line_1": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "zip_code": {"type": "string"}
                    },
                    "required": ["patient_id"]
                }
            }
        }
    ]

    return {
        "prompt": content,
        "tools": tools
    }
