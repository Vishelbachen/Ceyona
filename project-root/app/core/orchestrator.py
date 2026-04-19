from app.contracts.message import OrchestratorRequest
from app.engine.model_router import select_model
from app.engine.llm import run_llm
from app.core.logger import logger


class OrchestratorError(Exception):
    pass

async def run_llm(model: str, prompt: str, retries: int = 2, trace_id: str = None):

    try:
        logger.log(
            "INFO",
            "orchestrator_start",
            trace_id=trace_id
        )

        text = req.user_message.text

        model = select_model(text)

        response = await run_llm(
            model=model,
            prompt=text
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