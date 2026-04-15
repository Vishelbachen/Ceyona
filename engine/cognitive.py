from typing import Dict, Any


class Cognitive:
    async def build_context(
        self,
        user_id: int,
        text: str,
        memory: Dict[str, Any] | None = None,
        brain: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:

        memory = memory or {}
        brain = brain or {"domain": "general"}

        recent = memory.get("recent") or []
        semantic = memory.get("semantic") or []

        return {
            "user_id": user_id,
            "input": text,

            "brain": brain,

            "memory_recent": recent,
            "memory_semantic": semantic,

            "has_memory": bool(recent or semantic),
            "memory_strength": len(recent) + len(semantic),

            "history": recent + semantic
        }