from typing import Any, Dict, List, Optional


class SupabaseStore:
    """
    AI Platform v4.7 — Supabase Memory Store

    RESPONSIBILITY:
    - Persist and retrieve raw structured data
    - Provide CRUD interface over Supabase backend
    - Store conversation / usage / events

    STRICT RULES:
    - No semantic search logic
    - No ranking or retrieval intelligence
    - No LLM / reasoning usage
    - No access control or business decisions
    """

    def __init__(self, supabase_client: Any):
        self.client = supabase_client

    # =========================
    # WRITE OPERATIONS
    # =========================

    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserts a record into Supabase table.
        """

        response = self.client.table(table).insert(data).execute()

        return response.data if hasattr(response, "data") else {}

    def update(
        self,
        table: str,
        record_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Updates record in Supabase table.
        """

        response = (
            self.client.table(table)
            .update(data)
            .eq("id", record_id)
            .execute()
        )

        return response.data if hasattr(response, "data") else {}

    # =========================
    # READ OPERATIONS
    # =========================

    def get_by_id(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch single record by ID.
        """

        response = (
            self.client.table(table)
            .select("*")
            .eq("id", record_id)
            .execute()
        )

        data = response.data if hasattr(response, "data") else []

        return data[0] if data else None

    def query(
        self,
        table: str,
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Simple equality-based filtering only.
        """

        query = self.client.table(table).select("*")

        for key, value in filters.items():
            query = query.eq(key, value)

        response = query.execute()

        return response.data if hasattr(response, "data") else []

    # =========================
    # DELETE OPERATIONS
    # =========================

    def delete(self, table: str, record_id: str) -> Dict[str, Any]:
        """
        Deletes a record by ID.
        """

        response = (
            self.client.table(table)
            .delete()
            .eq("id", record_id)
            .execute()
        )

        return response.data if hasattr(response, "data") else {}