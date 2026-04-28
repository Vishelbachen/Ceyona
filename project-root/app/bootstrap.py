from functools import lru_cache
from app.settings import get_settings

from core.execution.orchestrator import Orchestrator


class Container:
    """
    AI Platform v4.7 — Dependency Injection Container
    LAZY INITIALIZATION (safe for Railway).
    """

    def __init__(self):
        self.settings = get_settings()

        self._auth = None
        self._rate_limiter = None
        self._retrieval_engine = None
        self._model_router = None
        self._orchestrator = None
        self._telegram_client = None

    # =========================
    # SECURITY
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

    # =========================
    # TELEGRAM OUTBOUND (FIXED ADDITION)
    # =========================

    @property
    def telegram_client(self):
        if self._telegram_client is None:
            from transport.telegram.client import TelegramClient
            self._telegram_client = TelegramClient(self.settings.BOT_TOKEN)
        return self._telegram_client

    # =========================
    # RETRIEVAL
    # =========================

    @property
    def retrieval_engine(self):
        if self._retrieval_engine is None:
            from retrieval.retrieval_engine import RetrievalEngine
            from memory.vector_memory import VectorMemory
            from memory.supabase_store import SupabaseStore

            self._retrieval_engine = RetrievalEngine(
                settings=self.settings,
                vector_memory=VectorMemory(self.settings),
                supabase_store=SupabaseStore(self.settings),
            )
        return self._retrieval_engine

    # =========================
    # LLM
    # =========================

    @property
    def model_router(self):
        if self._model_router is None:
            from llm.model_router import ModelRouter
            self._model_router = ModelRouter(self.settings)
        return self._model_router

    # =========================
    # ORCHESTRATOR (FIXED)
    # =========================

    @property
    def orchestrator(self):
        if self._orchestrator is None:
            from llm.prompt_engine import PromptEngine
            from agents.fast_agent import FastAgent
            from agents.deep_agent import DeepAgent
            from agents.creative_agent import CreativeAgent
            from agents.safety_agent import SafetyAgent
            from agents.consensus_engine import ConsensusEngine

            prompt_engine = PromptEngine()

            self._orchestrator = Orchestrator(
                settings=self.settings,
                retrieval_engine=self.retrieval_engine,
                model_router=self.model_router,
                agents={
                    "fast": FastAgent(self.model_router, prompt_engine),
                    "deep": DeepAgent(self.model_router, prompt_engine),
                    "creative": CreativeAgent(self.model_router, prompt_engine),
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