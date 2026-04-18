from app.contracts.message import OrchestratorRequest
from app.engine.model_router import select_model
from app.llm import run_llm


async def handle_request(req: OrchestratorRequest) -> str:
    model = select_model(req.user_message.text)

    response = await run_llm(
        model=model,
        prompt=req.user_message.text
    )

    return response.content