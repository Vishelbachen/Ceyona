from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse

from app.engine.model_decision import resolve_model
from app.engine.llm import run_llm
from app.engine.prompt_builder import PromptBuilder
from app.engine.reasoning_verifier import ReasoningVerifier

from app.engine.cognition.correction import Corrector
from app.engine.cognition.evaluation import Evaluator
from app.engine.cognition.reflection import Reflection

from app.core.logger import logger
from app.core.errors import OrchestratorError

from app.memory.memory_service import MemoryService
from app.infrastructure.supabase_store import SupabaseStore

from app.core.settings import settings


# -------------------------
# MAIN ORCHESTRATOR
# -------------------------
async def handle_request(
    req: OrchestratorRequest,
    memory: MemoryService | None = None
):

    trace_id = req.trace_id

    try:
        req.user_message.normalize()

        text = (req.user_message.text or "").strip()
        user_id = req.user_message.user_id

        logger.log("INFO", "orchestrator_start", trace_id=trace_id)

        if not text:
            raise ValueError("Empty input")

        # -------------------------
        # MEMORY LOAD
        # -------------------------
        context = []
        if memory and getattr(memory, "build_context", None):
            try:
                context = memory.build_context(user_id) or []
            except Exception as e:
                logger.log("WARN", "memory_load_failed", trace_id=trace_id, error=str(e))

        # -------------------------
        # MODEL DECISION
        # -------------------------
        model, intent_result, decision_meta = resolve_model(text)
        task_type = intent_result.task_type or "general"

        logger.log(
            "INFO",
            "model_selected",
            trace_id=trace_id,
            model=model,
            decision=decision_meta
        )

        # -------------------------
        # PROMPT BUILD
        # -------------------------
        prompt = PromptBuilder.build(
            user_text=text,
            context=context,
            model=model,
            task_type=task_type
        )

        # -------------------------
        # CORE LOOP
        # -------------------------
        max_attempts = 3
        final_answer = None
        last_response = ""
        current_model = model

        for attempt in range(max_attempts):

            logger.log(
                "INFO",
                "llm_attempt",
                trace_id=trace_id,
                attempt=attempt,
                model=current_model
            )

            response = await run_llm(
                model=current_model,
                prompt=prompt,
                trace_id=trace_id
            )

            last_response = (response.content or "").strip()

            # -------------------------
            # EVALUATION
            # -------------------------
            evaluation = Evaluator.evaluate(
                task_type=task_type,
                question=text,
                answer=last_response
            )

            if evaluation.is_valid:
                final_answer = last_response
                break

            logger.log(
                "WARN",
                "evaluation_failed",
                trace_id=trace_id,
                score=evaluation.score,
                issues=evaluation.issues
            )

            # -------------------------
            # VERIFIER
            # -------------------------
            verifier = ReasoningVerifier.verify(
                task_type=task_type,
                response=last_response
            )

            # -------------------------
            # ESCALATION
            # -------------------------
            if attempt == 0:
                prompt = Corrector.build_repair_prompt(
                    question=text,
                    answer=last_response,
                    issues=evaluation.issues
                )
                continue

            if attempt == 1:
                current_model = _upgrade_model(current_model)

                logger.log(
                    "INFO",
                    "model_upgraded",
                    trace_id=trace_id,
                    new_model=current_model
                )
                continue

        # -------------------------
        # FINAL FALLBACK
        # -------------------------
        final_answer = final_answer or last_response or "Unable to generate response."

        # -------------------------
        # MEMORY WRITE
        # -------------------------
        if memory and getattr(memory, "store", None):
            try:
                memory.store.append_message(user_id, "user", text)
                memory.store.append_message(user_id, "assistant", final_answer)
            except Exception as e:
                logger.log(
                    "ERROR",
                    "memory_save_failed",
                    trace_id=trace_id,
                    error=str(e)
                )

        # -------------------------
        # FINAL EVALUATION
        # -------------------------
        evaluation = Evaluator.evaluate(
            task_type=task_type,
            question=text,
            answer=final_answer
        )

        # -------------------------
        # REFLECTION LOG
        # -------------------------
        try:
            store = SupabaseStore()

            event = Reflection.build_event(
                user_id=user_id,
                question=text,
                answer=final_answer,
                model=current_model,
                task_type=task_type,
                evaluation=evaluation,
                trace_id=trace_id
            )

            store.insert_reflection("cognition_logs", event)

        except Exception as e:
            logger.log(
                "ERROR",
                "cognition_log_failed",
                trace_id=trace_id,
                error=str(e)
            )

        logger.log("INFO", "orchestrator_done", trace_id=trace_id)

        return SuccessResponse(
            data=final_answer,
            trace_id=trace_id,
            model=current_model,
            intent=intent_result.intent,
            task_type=task_type,
            reasoning_valid=evaluation.is_valid,
            confidence=evaluation.score
        )

    except Exception as e:

        logger.log(
            "ERROR",
            "orchestrator_crash",
            trace_id=trace_id,
            error=str(e)
        )

        return ErrorResponse(
            error={"message": str(e)},
            trace_id=trace_id
        )


# -------------------------
# MODEL ESCALATION
# -------------------------
def _upgrade_model(current: str) -> str:
    """
    fast → general → heavy
    """

    layers = ["fast", "general", "heavy"]

    for i, layer in enumerate(layers):
        models = settings.MODEL_LAYERS[layer]

        if current in models and i < len(layers) - 1:
            next_layer = layers[i + 1]
            return settings.MODEL_LAYERS[next_layer][0]

    return current