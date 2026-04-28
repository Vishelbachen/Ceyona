from functools import lru_cache
from app.settings import get_settings

from core.kernel.execution_policy_kernel import ExecutionPolicyKernel
from core.execution.orchestrator import Orchestrator


class Container:
    """
    AI Platform v4.7 — Dependency Injection Container
    LAZY INITIALIZATION (safe for Railway).
    """

    def __init__(self):
        self.settings = get_settings()

        # 🔒 core only
        self._auth = None
        self._rate_limiter = None
        self._retrieval_engine = None
        self._model_router = None
        self._orchestrator = None

    # =========================
    # LAZY PROPERTIES
    # =========================

    @property
    def auth(self):
        if self._auth is None:
            from security.auth import AuthService
            self._auth = AuthService(self.settings)
        return self._auth

    @property
    def rate_limiter(self):
        if self._rate_limiter is None:
            from security.rate_limiter import RateLimiter
            self._rate_limiter = RateLimiter(self.settings)
        return self._rate_limiter

    @property
    def retrieval_engine(self):
        if self._retrieval_engine is None:
            from retrieval.retrieval_engine import RetrievalEngine
            from retrieval.query_preprocessor import QueryPreprocessor
            from memory.vector_memory import VectorMemory
            from memory.supabase_store import SupabaseStore

            self._retrieval_engine = RetrievalEngine(
                settings=self.settings,
                vector_memory=VectorMemory(self.settings),
                supabase_store=SupabaseStore(self.settings),
            )
        return self._retrieval_engine

    @property
    def model_router(self):
        if self._model_router is None:
            from llm.model_router import ModelRouter
            self._model_router = ModelRouter(self.settings)
        return self._model_router

    @property
    def orchestrator(self):
        if self._orchestrator is None:
            from llm.prompt_engine import PromptEngine
            from llm.fallback_handler import FallbackHandler

            from agents.fast_agent import FastAgent
            from agents.deep_agent import DeepAgent
            from agents.creative_agent import CreativeAgent
            from agents.safety_agent import SafetyAgent
            from agents.consensus_engine import ConsensusEngine

            self._orchestrator = Orchestrator(
                retrieval_engine=self.retrieval_engine,
                model_router=self.model_router,
                agents={
                    "fast": FastAgent(self.model_router, PromptEngine()),
                    "deep": DeepAgent(self.model_router, PromptEngine()),
                    "creative": CreativeAgent(self.model_router, PromptEngine()),
                    "safety": SafetyAgent(self.model_router),
                },
                consensus_engine=ConsensusEngine(),
            )
        return self._orchestrator


# =========================
# SINGLETON
# =========================

@lru_cache(maxsize=1)
def get_container() -> Container:
    return Container()