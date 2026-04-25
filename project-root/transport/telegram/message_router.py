async def handle_update(update: dict):

    from core.cognition.intent_engine import build_intent
    from core.kernel.execution_policy_kernel import evaluate
    from payments.access_controller import check_access
    from agents.consensus import run_agents
    from llm.router import route_llm

    message = update["message"]["text"]

    intent = build_intent(message)

    decision = evaluate(intent)

    if decision == "DENY":
        return {"status": "denied"}

    wallet = update["message"]["from"]["id"]

    if not await check_access(wallet, intent):
        return {"status": "payment_required"}

    agent_output = await run_agents(intent)

    response = await route_llm(agent_output)

    return {"response": response}