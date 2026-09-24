"""
Voice AI Agent Telephony Webhooks & Function Calling Handlers
Supports Vapi, Retell, Bland.ai, and generic HTTP tool calls.
"""
import logging
import os
from typing import Dict, Any, List, Optional
import httpx
from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
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

    # Extract tool calls from any common wrapper
    tool_calls = None
    if isinstance(payload, dict):
        if "message" in payload and isinstance(payload["message"], dict):
            msg = payload["message"]
            tool_calls = msg.get("toolCalls") or msg.get("toolCallList") or msg.get("tool_calls")
        if not tool_calls:
            tool_calls = payload.get("toolCalls") or payload.get("toolCallList") or payload.get("tool_calls")

    if tool_calls and isinstance(tool_calls, list):
        results = []
        for call in tool_calls:
            tool_id = call.get("id") or call.get("toolCallId")
            func = call.get("function", {})
            name = func.get("name") or call.get("name")
            args = func.get("arguments", {}) if "function" in call else call.get("arguments", {})
            
            # If arguments is passed as JSON string
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            elif not isinstance(args, dict):
                args = {}

            res = execute_tool(name, args, db)
            results.append({"toolCallId": tool_id, "result": res})
        return {"results": results}

    # Case 2: Direct tool call format (Retell / Bland / Direct webhook)
    if "name" in payload and "arguments" in payload:
        name = payload["name"]
        args = payload["arguments"]
        if isinstance(args, str):
            import json
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        res = execute_tool(name, args, db)
        return {"result": res}

    # Case 3: Direct function call at root
    if "function" in payload:
        func = payload["function"]
        args = func.get("arguments", {})
        if isinstance(args, str):
            import json
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        res = execute_tool(func.get("name"), args, db)
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


def update_env_variable(key: str, value: str, env_path: str = ".env"):
    """Updates or appends a key-value pair in .env file safely."""
    lines = []
    key_found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            key_found = True
        else:
            new_lines.append(line)

    if not key_found:
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def mask_key(k: Optional[str]) -> str:
    """Masks secret key so it is never leaked in API responses."""
    if not k or len(k) < 8:
        return "••••••••••••••••"
    return f"{k[:4]}••••••••••••{k[-4:]}"


class SwitchVapiAccountRequest(BaseModel):
    private_key: str = Field(..., description="New Vapi Private API Key")
    public_key: Optional[str] = Field(None, description="New Vapi Public Key (optional)")


@router.get("/account-status", status_code=status.HTTP_200_OK, summary="Get Masked Vapi Account Info")
def get_vapi_account_status():
    """Returns masked credentials and telephony connection status without leaking secret keys."""
    key = settings.VAPI_API_KEY or os.getenv("VAPI_API_KEY", "")
    pub = settings.VAPI_PUBLIC_KEY or os.getenv("VAPI_PUBLIC_KEY", "")
    aid = settings.VAPI_ASSISTANT_ID or os.getenv("VAPI_ASSISTANT_ID", "")
    phone = settings.VAPI_PHONE_NUMBER or os.getenv("VAPI_PHONE_NUMBER", "+1 (463) 223-1253")

    return {
        "is_configured": bool(key),
        "masked_private_key": mask_key(key),
        "masked_public_key": mask_key(pub),
        "assistant_id": aid,
        "phone_number": phone
    }


@router.post("/switch-account", status_code=status.HTTP_200_OK, summary="Switch Vapi Telephony Account")
async def switch_vapi_account(payload: SwitchVapiAccountRequest):
    """
    Validates new Vapi credentials, provisions or links CareCloud intake assistant,
    and replaces old keys in .env.
    """
    new_private_key = payload.private_key.strip()
    new_public_key = (payload.public_key or "").strip()

    if not new_private_key:
        raise HTTPException(status_code=400, detail="Private API key cannot be empty.")

    headers = {
        "Authorization": f"Bearer {new_private_key}",
        "Content-Type": "application/json"
    }

    # 1. Validate credentials against Vapi
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            val_res = await client.get("https://api.vapi.ai/assistant", headers=headers)
            if val_res.status_code in (401, 403):
                raise HTTPException(status_code=400, detail="Invalid Vapi Private API Key. Authentication failed.")
            elif val_res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Vapi API returned HTTP {val_res.status_code}: {val_res.text[:100]}")
            
            assistants = val_res.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Vapi API: {str(e)}")

    # 2. Check for existing assistant or create one
    carecloud_assistant_id = None
    if isinstance(assistants, list):
        for a in assistants:
            if "carecloud" in a.get("name", "").lower():
                carecloud_assistant_id = a.get("id")
                break

    # Read prompt from file
    prompt_path = "prompts/patient_intake_prompt.md"
    prompt_text = "You are Alex, an intake coordinator at CareCloud."
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_text = f.read()

    webhook_url = settings.WEBHOOK_BASE_URL or os.getenv("WEBHOOK_BASE_URL", "https://carecloud-voice-ai.loca.lt")
    if not webhook_url.endswith("/voice/webhook"):
        webhook_url = f"{webhook_url}/voice/webhook"

    tools_spec = [
        {
            "type": "function",
            "function": {
                "name": "check_patient_by_phone",
                "description": "Check if a patient record exists by 10-digit phone number.",
                "parameters": {
                    "type": "object",
                    "properties": {"phone_number": {"type": "string"}},
                    "required": ["phone_number"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "register_patient",
                "description": "Create and persist a new patient demographic record.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "date_of_birth": {"type": "string"},
                        "sex": {"type": "string", "enum": ["Male", "Female", "Other", "Decline to Answer"]},
                        "phone_number": {"type": "string"},
                        "address_line_1": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "zip_code": {"type": "string"}
                    },
                    "required": ["first_name", "last_name", "date_of_birth", "sex", "phone_number", "address_line_1", "city", "state", "zip_code"]
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
                    "properties": {"patient_id": {"type": "string"}},
                    "required": ["patient_id"]
                }
            }
        },
        {
            "type": "endCall",
            "function": {
                "name": "end_call",
                "description": "Disconnects and terminates the call immediately."
            }
        }
    ]

    async with httpx.AsyncClient(timeout=15.0) as client:
        if not carecloud_assistant_id:
            # Create new assistant in this account
            create_payload = {
                "name": "CareCloud Intake Coordinator",
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "system", "content": prompt_text}],
                    "tools": tools_spec
                },
                "firstMessage": "Thank you for calling CareCloud Patient Registration! My name is Alex. I can help you register as a new patient today. To get started, could I please have your first and last name?",
                "serverUrl": webhook_url,
                "endCallPhrases": ["goodbye", "have a great day", "bye now", "that is all"]
            }
            c_res = await client.post("https://api.vapi.ai/assistant", headers=headers, json=create_payload)
            if c_res.status_code in (200, 201):
                carecloud_assistant_id = c_res.json().get("id")
        else:
            await client.patch(
                f"https://api.vapi.ai/assistant/{carecloud_assistant_id}",
                headers=headers,
                json={"serverUrl": webhook_url}
            )

        # 3. Check for provisioned phone number in this new account
        phone_number_str = None
        phone_id = None
        p_res = await client.get("https://api.vapi.ai/phone-number", headers=headers)
        if p_res.status_code == 200:
            phones = p_res.json()
            if phones and isinstance(phones, list) and len(phones) > 0:
                phone_obj = phones[0]
                phone_id = phone_obj.get("id")
                phone_number_str = phone_obj.get("number")
                if carecloud_assistant_id and phone_id:
                    await client.patch(
                        f"https://api.vapi.ai/phone-number/{phone_id}",
                        headers=headers,
                        json={"assistantId": carecloud_assistant_id}
                    )

    # 4. Safely update .env file and overwrite old keys
    env_path = ".env"
    env_updates = {
        "VAPI_API_KEY": new_private_key,
        "VAPI_PUBLIC_KEY": new_public_key,
        "VAPI_ASSISTANT_ID": carecloud_assistant_id or "",
    }
    if phone_id:
        env_updates["VAPI_PHONE_NUMBER_ID"] = phone_id
    if phone_number_str:
        env_updates["VAPI_PHONE_NUMBER"] = phone_number_str

    for k, v in env_updates.items():
        update_env_variable(k, v, env_path)
        os.environ[k] = v
        if hasattr(settings, k):
            setattr(settings, k, v)

    logger.info(f"Switched Vapi account to assistant: {carecloud_assistant_id}, phone: {phone_number_str}")

    return {
        "status": "success",
        "message": "Vapi account switched successfully!",
        "assistant_id": carecloud_assistant_id,
        "phone_number": phone_number_str or "No phone number provisioned yet in this account",
        "masked_private_key": mask_key(new_private_key)
    }
