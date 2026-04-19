from app.contracts.message import OrchestratorRequest
from app.engine.model_router import select_model
from app.engine.llm import run_llm as llm_run  # 🔥 важно: алиас
from app.core.logger import logger


class OrchestratorError(Exception):
    pass


async def handle_request(req: OrchestratorRequest) -> str:
    trace_id = req.trace_id

    try:
        logger.log(
            "INFO",
            "orchestrator_start",
            trace_id=trace_id
        )

        # 📌 входной текст
        text = req.user_message.text

        # 📌 выбор модели
        model = select_model(text)

        logger.log(
            "INFO",
            "model_selected",
            trace_id=trace_id,
            model=model
        )

        # 📌 вызов LLM (ВАЖНО: через алиас)
        response = await llm_run(
            model=model,
            prompt=text,
            trace_id=trace_id
        )

        logger.log(
            "INFO",
            "orchestrator_done",
            trace_id=trace_id
        )

        return response.content

    except Exception as e:
        logger.log(
            "ERROR",
            "orchestrator_error",
            trace_id=trace_id,
            error=str(e)
        )
        return f"Error: {str(e)}"