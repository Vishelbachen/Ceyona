from app.contracts.message import OrchestratorRequest
from app.engine.model_router import select_model
from app.engine.llm import run_llm


class OrchestratorError(Exception):
    pass


async def handle_request(req: OrchestratorRequest) -> str:
    try:
        if not req.user_message or not req.user_message.text:
            raise OrchestratorError("Empty message")

        text = req.user_message.text

        model = select_model(text)

        response = await run_llm(
            model=model,
            prompt=text
        )

        return response.content

    except Exception as e:
        return f"Error: {str(e)}"