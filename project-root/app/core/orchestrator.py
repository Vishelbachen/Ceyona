from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse

from app.engine.model_decision import resolve_model
from app.engine.llm import run_llm
from app.engine.intent_classifier import classify_intent

from app.core.logger import logger
from app.core.errors import OrchestratorError

from app.memory.memory_service import MemoryService
from app.core.prompt_builder import PromptBuilder

from app.core.reasoning_verifier import ReasoningVerifier
from app.cognition.correction import Corrector

from app.cognition.evaluation import Evaluator
from app.cognition.reflection import Reflection
from app.memory.supabase_store import SupabaseStore


# -------------------------
# MAIN ORCHESTRATOR
# -------------------------
async def handle_request(req: OrchestratorRequest, memory: MemoryService | None = None):

    trace_id = req.trace_id

    try:
        # 🧠 normalize input (important fix)
        req.user_message.normalize()

        text = (req.user_message.text or "").strip()
        user_id = req.user_message.user_id

        logger.log("INFO", "orchestrator_start", trace_id=trace_id)

        if not text:
            raise ValueError("Empty input")

        # -------------------------
        # MEMORY LOAD (SAFE)
        # -------------------------
        context = []
        if memory and getattr(memory, "build_context", None):
            try:
                context = memory.build_context(user_id) or []
            except Exception as e:
                logger.log("WARN", "memory_load_failed", trace_id=trace_id, error=str(e))

        # -------------------------
        # INTENT CLASSIFICATION
        # -------------------------
        intent_result = classify_intent(text)

        # FIX: task_type must come from structured field (not intent name)
        task_type = getattr(intent_result, "task_type", None) or "general"

        # -------------------------
        # MODEL DECISION
        # -------------------------
        model, intent_result = resolve_model(text)

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
        max_attempts = 2
        final_answer = None
        last_response = ""

        for attempt in range(max_attempts):

            logger.log(
                "INFO",
                "llm_attempt",
                trace_id=trace_id,
                attempt=attempt
            )

            response = await run_llm(
                model=model,
                prompt=prompt,
                trace_id=trace_id
            )

            last_response = (response.content or "").strip()

            # -------------------------
            # VERIFIER
            # -------------------------
            check = ReasoningVerifier.verify(
                task_type=task_type,
                question=text,
                answer=last_response
            )

            if check["is_valid"]:
                final_answer = last_response
                break

            logger.log(
                "WARN",
                "verifier_failed",
                trace_id=trace_id,
                issues=check["issues"]
            )

            # -------------------------
            # CORRECTOR (SAFE REPAIR LOOP)
            # -------------------------
            prompt = Corrector.build_repair_prompt(
                question=text,
                answer=last_response,
                issues=check["issues"],
                context=context
            )

        # -------------------------
        # FINAL FALLBACK
        # -------------------------
        final_answer = final_answer or last_response or "Unable to generate response."

        # -------------------------
        # MEMORY WRITE (SAFE)
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
        # EVALUATION
        # -------------------------
        evaluation = Evaluator.evaluate(
            task_type=task_type,
            question=text,
            answer=final_answer
        )

        # -------------------------
        # SUPABASE REFLECTION LOG
        # -------------------------
        try:
            store = SupabaseStore()

            event = Reflection.build_event(
                user_id=user_id,
                question=text,
                answer=final_answer,
                model=model,
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

        # -------------------------
        # FINAL RESPONSE (FIXED + COMPLETE METADATA)
        # -------------------------
        return SuccessResponse(
            data=final_answer,
            trace_id=trace_id,
            model=model,
            intent=intent_result.intent,
            task_type=task_type,
            reasoning_valid=getattr(evaluation, "is_valid", None),
            confidence=getattr(evaluation, "score", None)
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