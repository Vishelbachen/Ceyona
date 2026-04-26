from __future__ import annotations

from typing import Optional, Dict, Any, List

try:
    from supabase import create_client, Client
except ImportError:  # optional dependency
    create_client = None
    Client = None


# =========================
# SUPABASE STORE
# =========================
class SupabaseStore:
    """
    ROLE:
    - persistent storage adapter (Supabase)
    - store and retrieve structured data

    STRICT RULES:
    - no business logic
    - no data interpretation
    - no schema decisions at runtime
    - fail-safe (must not break system)
    """

    def __init__(
        self,
        url: Optional[str],
        key: Optional[str],
        table: str = "memory",
    ):
        self._enabled = bool(url and key and create_client)
        self._table = table
        self._client: Optional[Client] = None

        if self._enabled:
            self._client = create_client(url, key)

    # =========================
    # INSERT
    # =========================
    def insert(self, data: Dict[str, Any]) -> None:

        if not self._enabled:
            return

        try:
            self._client.table(self._table).insert(data).execute()
        except Exception:
            pass

    # =========================
    # UPSERT
    # =========================
    def upsert(self, data: Dict[str, Any]) -> None:

        if not self._enabled:
            return

        try:
            self._client.table(self._table).upsert(data).execute()
        except Exception:
            pass

    # =========================
    # GET BY FIELD
    # =========================
    def get(
        self,
        field: str,
        value: Any,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:

        if not self._enabled:
            return []

        try:
            response = (
                self._client
                .table(self._table)
                .select("*")
                .eq(field, value)
                .limit(limit)
                .execute()
            )

            return response.data or []

        except Exception:
            return []

    # =========================
    # DELETE
    # =========================
    def delete(
        self,
        field: str,
        value: Any,
    ) -> None:

        if not self._enabled:
            return

        try:
            self._client.table(self._table).delete().eq(field, value).execute()
        except Exception:
            pass

    # =========================
    # HEALTHCHECK (OPTIONAL)
    # =========================
    def is_available(self) -> bool:
        return self._enabled and self._client is not None