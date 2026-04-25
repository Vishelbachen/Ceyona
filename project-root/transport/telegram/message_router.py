async def handle_update(update: dict):

    from core.cognition.intent_engine import build_intent
    from core.kernel.execution_policy_kernel import evaluate
    from payments.access_controller import check_access
    from agents.consensus import run_agents
    from llm.router import route_llm

    # 🔥 SAFE EXTRACT (CRITICAL FIX)
    message_obj = update.get("message") or update.get("edited_message")

    if not message_obj:
        return None

    message = message_obj.get("text")
    if not message:
        return None

    chat_id = message_obj["chat"]["id"]

    intent = build_intent(message)

    decision = evaluate(intent)

    if decision == "DENY":
        return {"chat_id": chat_id, "text": "⛔ denied"}

    wallet = message_obj["from"]["id"]

    if not await check_access(wallet, intent):
        return {"chat_id": chat_id, "text": "💳 payment required"}

    agent_output = await run_agents(intent)

    response = await route_llm(agent_output)

    return {"chat_id": chat_id, "text": str(response)}