from functools import lru_cache

from app.settings import get_settings

# =========================
# CORE IMPORTS (CONTRACT LAYER)
# =========================
from core.kernel.execution_policy_kernel import ExecutionPolicyKernel
from core.execution.orchestrator import Orchestrator

# =========================
# LLM LAYER
# =========================
from llm.model_router import ModelRouter
from llm.prompt_engine import PromptEngine
from llm.fallback_handler import FallbackHandler

# =========================
# RETRIEVAL LAYER
# =========================
from retrieval.retrieval_engine import RetrievalEngine
from retrieval.query_preprocessor import QueryPreprocessor

# =========================
# MEMORY LAYER
# =========================
from memory.supabase_store import SupabaseStore
from memory.vector_memory import VectorMemory
from memory.conversation_history import ConversationHistory

# =========================
# AGENTS
# =========================
from agents.fast_agent import FastAgent
from agents.deep_agent import DeepAgent
from agents.creative_agent import CreativeAgent
from agents.safety_agent import SafetyAgent
from agents.consensus_engine import ConsensusEngine

# =========================
# SECURITY
# =========================
from security.auth import AuthService
from security.rate_limiter import RateLimiter


class Container:
    """
    AI Platform v4.7 — Dependency Injection Container
    PURE WIRING ONLY (no logic, no decisions).
    """

    def __init__(self):
        self.settings = get_settings()

        # =========================
        # SECURITY
        # =========================
        self.auth = AuthService(self.settings)
        self.rate_limiter = RateLimiter(self.settings)

        # =========================
        # MEMORY / STORAGE
        # =========================
        self.supabase_store = SupabaseStore(self.settings)
        self.vector_memory = VectorMemory(self.settings)
        self.conversation_history = ConversationHistory(self.settings)

        # =========================
        # RETRIEVAL LAYER
        # =========================
        self.query_preprocessor = QueryPreprocessor()
        self.retrieval_engine = RetrievalEngine(
            settings=self.settings,
            vector_memory=self.vector_memory,
            supabase_store=self.supabase_store,
        )

        # =========================
        # LLM LAYER
        # =========================
        self.model_router = ModelRouter(self.settings)
        self.prompt_engine = PromptEngine()
        self.fallback_handler = FallbackHandler()

        # =========================
        # AGENTS
        # =========================
        self.fast_agent = FastAgent(self.model_router, self.prompt_engine)
        self.deep_agent = DeepAgent(self.model_router, self.prompt_engine)
        self.creative_agent = CreativeAgent(self.model_router, self.prompt_engine)
        self.safety_agent = SafetyAgent(self.model_router)
        self.consensus_engine = ConsensusEngine()

        # =========================
        # EXECUTION CORE
        # =========================
        self.execution_policy_kernel = ExecutionPolicyKernel(self.settings)
        self.orchestrator = Orchestrator(
            retrieval_engine=self.retrieval_engine,
            model_router=self.model_router,
            agents={
                "fast": self.fast_agent,
                "deep": self.deep_agent,
                "creative": self.creative_agent,
                "safety": self.safety_agent,
            },
            consensus_engine=self.consensus_engine,
        )


# =========================
# SINGLETON ACCESSOR
# =========================

@lru_cache(maxsize=1)
def get_container() -> Container:
    """
    Global DI container singleton.
    Initialized once per process.
    """
    return Container()