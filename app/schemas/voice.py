"""
Voice Agent Webhook & Tool-Calling Schemas
Compatible with standard Voice AI platforms (Vapi, Retell, Bland.ai)
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class FunctionCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolCall(BaseModel):
    id: Optional[str] = "call_default"
    type: str = "function"
    function: FunctionCall


class VoiceWebhookRequest(BaseModel):
    """Generic or Vapi/Retell tool-call request wrapper."""
    message: Optional[Dict[str, Any]] = None
    toolCalls: Optional[List[ToolCall]] = None
    name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None


class ToolCallResult(BaseModel):
    toolCallId: Optional[str] = None
    result: Any


class VoiceWebhookResponse(BaseModel):
    results: Optional[List[ToolCallResult]] = None
    response: Optional[str] = None
    data: Optional[Any] = None
