import logging
from dataclasses import dataclass

from llm.hf_client import BGE_LARGE, BGE_SMALL, hf_client

logger = logging.getLogger(__name__)


@dataclass
class DenseResult:
    embedding: list[float]
    model: str
    tokens_used: int


class BGEEngine:
    """
    Dense embedding engine using BGE models via HF.
    Generates vectors only. No interpretation.
    """

    async def embed(
        self,
        text: str,
        use_fast: bool = False,
    ) -> DenseResult | None:
        model = BGE_SMALL if use_fast else BGE_LARGE
        try:
            vectors = await hf_client.embed([text], model=model)
            if not vectors:
                return None
            # rough token estimate: chars / 4
            tokens = max(1, len(text) // 4)
            return DenseResult(
                embedding=vectors[0],
                model=model,
                tokens_used=tokens,
            )
        except Exception as exc:
            logger.error("BGEEngine.embed failed", extra={"error": str(exc)})
            return None


bge_engine = BGEEngine()