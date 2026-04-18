from pydantic import BaseModel
from typing import Optional, Dict, Any


class UserMessage(BaseModel):
    user_id: str
    text: str
    metadata: Optional[Dict[str, Any]] = None


class OrchestratorRequest(BaseModel):
    user_message: UserMessage


class LLMRequest(BaseModel):
    model: str
    prompt: str
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMResponse(BaseModel):
    content: str
    raw: Optional[Dict[str, Any]] = None