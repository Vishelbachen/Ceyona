from engine.orchestrator import Orchestrator

orchestrator = Orchestrator()


async def handle_message(user_id: int, text: str) -> str:
    try:
        result = await orchestrator.process(
            user_id=user_id,
            text=text
        )
        return result
    except Exception as e:
        return f"Error: {str(e)}"