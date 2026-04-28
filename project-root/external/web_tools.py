from typing import Any, Dict, Optional
import json


class WebToolsClient:
    """
    AI Platform v4.7 — Web Tools Client

    RESPONSIBILITY:
    - Perform raw HTTP requests (GET/POST)
    - Fetch external web resources
    - Return unprocessed response data

    STRICT RULES:
    - No HTML parsing logic
    - No content summarization
    - No LLM / retrieval / memory usage
    - No decision-making
    - No data interpretation
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Performs raw HTTP GET request.
        """

        return {
            "url": url,
            "status_code": 200,
            "headers": headers or {},
            "body": "<raw html or json response>",
        }

    async def post(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Performs raw HTTP POST request.
        """

        return {
            "url": url,
            "status_code": 200,
            "sent_payload": payload,
            "headers": headers or {},
            "body": json.dumps({"mock": "response"}),
        }

    async def fetch_json(
        self,
        url: str,
    ) -> Dict[str, Any]:
        """
        Convenience wrapper for JSON endpoints (no parsing logic).
        """

        return {
            "url": url,
            "json": {"mock": "data"},
        }