from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse

from app.engine.model_decision import resolve_model
from app.engine.llm import run_llm

from app.core.logger import logger
from app.core.errors import OrchestratorError

from app.memory.memory_service import MemoryService
from app.core.prompt_builder import PromptBuilder

from app.core.reasoning_verifier import ReasoningVerifier
from app.engine.task_classifier import classify
from app.cognition.correction import Corrector

# 🧠 COGNITION LAYER (NEW)
from app.cognition.evaluation import Evaluator
from app.cognition.reflection import Reflection
from app.memory.supabase_store import SupabaseStore


# -------------------------
# MAIN ORCHESTRATOR
# -------------------------
async def handle_request(req: OrchestratorRequest, memory: MemoryService | None = None):

    trace_id = req.trace_id

    try:
        logger.log("INFO", "orchestrator_start", trace_id=trace_id)

        text = (req.user_message.text or "").strip()
        user_id = req.user_message.user_id

        if not text:
            raise ValueError("Empty input")

        # -------------------------
        # MEMORY
        # -------------------------
        context = memory.build_context(user_id) if memory else []

        # -------------------------
        # ROUTING
        # -------------------------
        model, intent = resolve_model(text)
        task_type = classify(text)

        # -------------------------
        # BASE PROMPT
        # -------------------------
        prompt = PromptBuilder.build(
            user_text=text,
            context=context,
            model=model
        )

        # -------------------------
        # CORE LOOP (LLM + VERIFIER + CORRECTION)
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

            last_response = response.content or ""

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
            # CORRECTION STEP
            # -------------------------
            prompt = Corrector.build_repair_prompt(
                question=text,
                answer=last_response,
                issues=check["issues"]
            )

        # -------------------------
        # FINAL FALLBACK SAFETY
        # -------------------------
        if not final_answer:
            final_answer = last_response or "Unable to generate response."

        # -------------------------
        # MEMORY WRITE (SHORT TERM)
        # -------------------------
        if memory and getattr(memory, "store", None):
            try:
                memory.store.append_message(user_id, "user", text)
                memory.store.append_message(user_id, "assistant", final_answer)

                logger.log("INFO", "memory_saved", trace_id=trace_id)

            except Exception as e:
                logger.log("ERROR", "memory_save_failed", trace_id=trace_id, error=str(e))

        # -------------------------
        # 🧠 COGNITION EVALUATION (NEW)
        # -------------------------
        evaluation = Evaluator.evaluate(
            task_type=task_type,
            question=text,
            answer=final_answer
        )

        # -------------------------
        # 🧠 SUPABASE REFLECTION LOGGING (NEW)
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

            logger.log("INFO", "cognition_logged", trace_id=trace_id)

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
            trace_id=trace_id
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