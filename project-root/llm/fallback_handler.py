from __future__ import annotations

from typing import Dict, Any, List, Optional

from llm.model_router import ModelRouter
from llm.groq_client import GroqClient
from llm.hf_client import HFClient


# =========================
# FALLBACK HANDLER
# =========================
class FallbackHandler:
    """
    ROLE:
    - handle model execution failure fallback
    - switch between providers (Groq ↔ HF)
    - provide deterministic retry path

    STRICT RULES:
    - no prompt modification
    - no reasoning
    - no intent analysis
    - no model selection logic beyond static fallback order
    """

    def __init__(
        self,
        groq: GroqClient,
        hf: HFClient,
        router: ModelRouter,
    ):
        self._groq = groq
        self._hf = hf
        self._router = router

    # =========================
    # EXECUTE WITH FALLBACK
    # =========================
    def execute(
        self,
        tier: str,
        model: str,
        messages: List[Dict[str, str]],
        *,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> str:

        # candidate models from router
        candidates = self._router.resolve_candidates(tier)

        # build execution order
        execution_chain = self._build_chain(model, candidates)

        last_error: Optional[Exception] = None

        for provider, model_name in execution_chain:

            try:
                if provider == "groq":
                    return self._groq.chat(
                        model=model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )

                if provider == "hf":
                    return self._hf.chat(
                        model=model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )

            except Exception as e:
                last_error = e
                continue

        # if everything fails → hard fail
        raise RuntimeError(
            f"All LLM providers failed for tier={tier}"
        ) from last_error

    # =========================
    # BUILD EXECUTION CHAIN
    # =========================
    def _build_chain(
        self,
        primary_model: str,
        candidates: Dict[str, str],
    ) -> List[tuple[str, str]]:

        """
        Deterministic fallback order:

        1. primary provider (inferred)
        2. alternative models
        3. cross-provider fallback
        """

        chain: List[tuple[str, str]] = []

        # heuristic provider mapping (STATIC ONLY)
        chain.append(self._infer_provider(primary_model, candidates))

        # add candidates
        for _, model in candidates.items():
            chain.append(self._infer_provider(model, candidates))

        # deduplicate preserving order
        seen = set()
        result = []

        for item in chain:
            if item not in seen:
                seen.add(item)
                result.append(item)

        return result

    # =========================
    # PROVIDER INFERENCE (STATIC)
    # =========================
    def _infer_provider(
        self,
        model: str,
        candidates: Dict[str, str],
    ) -> tuple[str, str]:

        """
        VERY IMPORTANT:
        This is NOT intelligent routing.

        It is a static mapping rule layer.
        """

        # HF models usually explicit repo names or known families
        if "/" in model or "llama" in model or "qwen" in model:
            return ("hf", model)

        # Groq hosted models (explicit known set)
        return ("groq", model)