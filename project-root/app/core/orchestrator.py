from app.contracts.message import OrchestratorRequest
from app.contracts.response import SuccessResponse, ErrorResponse
from app.engine.model_router import select_model
from app.engine.llm import run_llm
from app.core.logger import logger
from app.core.errors import OrchestratorError


async def handle_request(req: OrchestratorRequest):
    trace_id = req.trace_id

    try:
        logger.log("INFO", "orchestrator_start", trace_id=trace_id)

        text = req.user_message.text

        model = select_model(text)

        logger.log(
            "INFO",
            "model_selected",
            trace_id=trace_id,
            model=model
        )

        response = await run_llm(
            model=model,
            prompt=text,
            trace_id=trace_id
        )

        logger.log("INFO", "orchestrator_done", trace_id=trace_id)

        return SuccessResponse(
            data=response.content,
            trace_id=trace_id
        )

    except OrchestratorError as e:
        return ErrorResponse(
            error=e.to_dict()["error"],
            trace_id=trace_id
        )

    except Exception as e:
        logger.log(
            "ERROR",
            "orchestrator_error",
            trace_id=trace_id,
            error=str(e)
        )

        err = OrchestratorError(
            code="ORCH_001",
            message=str(e),
            layer="orchestrator",
            trace_id=trace_id
        )

        return ErrorResponse(
            error=err.to_dict()["error"],
            trace_id=trace_id
        )