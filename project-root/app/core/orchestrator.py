from app.contracts.message import OrchestratorRequest, LLMRequest
from app.engine.model_router import select_model
from app.llm import run_llm


class OrchestratorError(Exception):
    pass


async def handle_request(req: OrchestratorRequest) -> str:
    try:
        # 1. VALIDATION LAYER (контроль входа)
        if not req.user_message or not req.user_message.text:
            raise OrchestratorError("Empty user message")

        text = req.user_message.text

        # 2. ROUTING LAYER
        model = select_model(text)

        if not model:
            raise OrchestratorError("Model selection failed")

        # 3. BUILD LLM REQUEST (контракт)
        llm_request = LLMRequest(
            model=model,
            prompt=text
        )

        # 4. EXECUTION LAYER
        response = await run_llm(
            model=llm_request.model,
            prompt=llm_request.prompt
        )

        if not response or not response.content:
            raise OrchestratorError("Empty LLM response")

        # 5. OUTPUT
        return response.content

    except OrchestratorError as e:
        return f"Orchestrator error: {str(e)}"

    except Exception as e:
        # защита от падения всей системы
        return f"Unexpected system error: {str(e)}"