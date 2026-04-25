async def handle_update(update: dict):

    # lazy imports (IMPORTANT)
    from core.cognition.intent_engine import build_intent
    from core.kernel.execution_policy_kernel import evaluate
    from payments.access_controller import check_access
    from agents.consensus import run_agents
    from llm.router import route_llm

    message = update["message"]["text"]
    chat_id = update["message"]["chat"]["id"]

    intent = build_intent(message)

    decision = evaluate(intent)

    # ❗ вместо return → просто текст-ответ внутри системы
    if decision == "DENY":
        return {
            "chat_id": chat_id,
            "text": "⛔ denied"
        }

    wallet = update["message"]["from"]["id"]

    if not await check_access(wallet, intent):
        return {
            "chat_id": chat_id,
            "text": "💳 payment required"
        }

    agent_output = await run_agents(intent)

    response = await route_llm(agent_output)

    return {
        "chat_id": chat_id,
        "text": str(response)
    }