from typing import Dict, Any


class Cognitive:
    async def build_context(
        self,
        user_id: int,
        text: str,
        memory: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Cognitive layer:
        - merges raw input
        - merges memory layer
        - prepares structured context for reasoning + solver
        """

        memory = memory or {}

        recent = memory.get("recent", [])
        semantic = memory.get("semantic", [])

        return {
            "user_id": user_id,
            "input": text,

            # raw memory signals
            "memory_recent": recent,
            "memory_semantic": semantic,

            # structured context flags (for reasoning)
            "has_memory": bool(recent or semantic),
            "memory_strength": len(recent) + len(semantic),

            # unified history view (future expansion)
            "history": recent + semantic
        }