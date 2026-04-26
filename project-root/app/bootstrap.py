from dataclasses import dataclass

from app.settings import get_settings

# Core
from core.execution.orchestrator import Orchestrator
from core.kernel.execution_policy_kernel import ExecutionPolicyKernel

# Cognition
from cognition.intent_engine import IntentEngine
from cognition.reasoning_engine import ReasoningEngine
from cognition.multi_agent_coordinator import MultiAgentCoordinator
from cognition.response_synthesizer import ResponseSynthesizer

# LLM
from llm.model_router import ModelRouter
from llm.prompt_engine import PromptEngine
from llm.fallback_handler import FallbackHandler
from llm.groq_client import GroqClient
from llm.hf_client import HFClient

# Memory
from memory.supabase_store import SupabaseStore
from memory.vector_memory import VectorMemory
from memory.conversation_history import ConversationHistory

# Retrieval
from retrieval.retrieval_engine import RetrievalEngine
from retrieval.query_preprocessor import QueryPreprocessor

# Context
from context.assembler import ContextAssembler
from context.serializer import ContextSerializer

# Security
from security.auth import AuthService
from security.encryption import EncryptionService
from security.rate_limiter import RateLimiter
from security.origin_guard import OriginGuard

# Observability
from observability.logger import Logger
from observability.metrics import Metrics
from observability.tracing import Tracer

# Events
from events.event_bus import EventBus
from events.event_store import EventStore


# =========================
# 🧩 DI CONTAINER (LIGHTWEIGHT)
# =========================
@dataclass
class Container:
    # Core
    orchestrator: Orchestrator
    epk: ExecutionPolicyKernel

    # Cognition
    intent_engine: IntentEngine
    reasoning_engine: ReasoningEngine
    multi_agent: MultiAgentCoordinator
    response_synthesizer: ResponseSynthesizer

    # LLM
    model_router: ModelRouter
    prompt_engine: PromptEngine
    fallback: FallbackHandler

    # Memory
    memory_store: SupabaseStore
    vector_memory: VectorMemory
    conversation_history: ConversationHistory

    # Retrieval
    retrieval_engine: RetrievalEngine
    query_preprocessor: QueryPreprocessor

    # Context
    context_assembler: ContextAssembler
    context_serializer: ContextSerializer

    # Security
    auth: AuthService
    encryption: EncryptionService
    rate_limiter: RateLimiter
    origin_guard: OriginGuard

    # Observability
    logger: Logger
    metrics: Metrics
    tracer: Tracer

    # Events
    event_bus: EventBus
    event_store: EventStore


# =========================
# ⚙️ BOOTSTRAP FUNCTION
# =========================
def build_container() -> Container:
    """
    Composition root of the entire system.
    NO BUSINESS LOGIC ALLOWED HERE.
    ONLY WIRING.
    """

    settings = get_settings()

    # =========================
    # OBSERVABILITY FIRST (base dependency)
    # =========================
    logger = Logger()
    metrics = Metrics()
    tracer = Tracer()

    # =========================
    # EVENTS (observability layer)
    # =========================
    event_bus = EventBus(logger=logger)
    event_store = EventStore()

    # =========================
    # SECURITY
    # =========================
    auth = AuthService(settings.JWT_SECRET)
    encryption = EncryptionService(settings.ENCRYPTION_KEY)
    rate_limiter = RateLimiter(settings.REDIS_URL)
    origin_guard = OriginGuard(settings.ALLOWED_ORIGINS)

    # =========================
    # MEMORY
    # =========================
    memory_store = SupabaseStore(
        url=settings.SUPABASE_URL,
        anon_key=settings.SUPABASE_ANON_KEY,
        service_key=settings.SUPABASE_SERVICE_ROLE_KEY,
    )

    vector_memory = VectorMemory(redis_url=settings.REDIS_URL)
    conversation_history = ConversationHistory(memory_store)

    # =========================
    # RETRIEVAL
    # =========================
    query_preprocessor = QueryPreprocessor()

    retrieval_engine = RetrievalEngine(
        vector_memory=vector_memory,
        query_preprocessor=query_preprocessor,
    )

    # =========================
    # CONTEXT
    # =========================
    context_assembler = ContextAssembler()
    context_serializer = ContextSerializer()

    # =========================
    # LLM LAYER
    # =========================
    groq = GroqClient(settings.GROQ_API_KEY)
    hf = HFClient(settings.HF_TOKEN)

    model_router = ModelRouter(
        groq=groq,
        hf=hf,
    )

    prompt_engine = PromptEngine()
    fallback = FallbackHandler()

    # =========================
    # COGNITION
    # =========================
    intent_engine = IntentEngine()
    reasoning_engine = ReasoningEngine()

    multi_agent = MultiAgentCoordinator(
        intent_engine=intent_engine,
        reasoning_engine=reasoning_engine,
    )

    response_synthesizer = ResponseSynthesizer()

    # =========================
    # CORE
    # =========================
    epk = ExecutionPolicyKernel()

    orchestrator = Orchestrator(
        epk=epk,
        model_router=model_router,
        prompt_engine=prompt_engine,
        retrieval_engine=retrieval_engine,
        context_assembler=context_assembler,
        response_synthesizer=response_synthesizer,
        memory=conversation_history,
        event_bus=event_bus,
    )

    # =========================
    # FINAL CONTAINER
    # =========================
    return Container(
        orchestrator=orchestrator,
        epk=epk,
        intent_engine=intent_engine,
        reasoning_engine=reasoning_engine,
        multi_agent=multi_agent,
        response_synthesizer=response_synthesizer,
        model_router=model_router,
        prompt_engine=prompt_engine,
        fallback=fallback,
        memory_store=memory_store,
        vector_memory=vector_memory,
        conversation_history=conversation_history,
        retrieval_engine=retrieval_engine,
        query_preprocessor=query_preprocessor,
        context_assembler=context_assembler,
        context_serializer=context_serializer,
        auth=auth,
        encryption=encryption,
        rate_limiter=rate_limiter,
        origin_guard=origin_guard,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        event_bus=event_bus,
        event_store=event_store,
    )


# =========================
# 🌍 GLOBAL ENTRY (SAFE)
# =========================
_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = build_container()
    return _container