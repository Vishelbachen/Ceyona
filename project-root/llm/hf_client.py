from typing import Any, Dict, List, Optional


class HFClient:
    """
    AI Platform v4.7 — Hugging Face Inference Client

    RESPONSIBILITY:
    - Send inference requests to Hugging Face models
    - Return raw model outputs
    - Act as thin external API adapter

    STRICT RULES:
    - No model routing logic
    - No prompt engineering
    - No fallback logic
    - No retrieval / memory access
    - No orchestration decisions
    """

    def __init__(self, api_token: str, base_url: Optional[str] = None):
        self.api_token = api_token
        self.base_url = base_url or "https://api-inference.huggingface.co"

    async def text_generation(
        self,
        model: str,
        inputs: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Sends text generation request to HF Inference API.
        """

        return {
            "model": model,
            "generated_text": "mock hf response",
            "parameters_used": parameters or {},
        }

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Chat-style inference wrapper.
        """

        return {
            "model": model,
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "mock hf chat response",
                    }
                }
            ],
            "parameters_used": parameters or {},
        }