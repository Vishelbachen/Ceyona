async def handle_update(update: dict):

    try:
        from core.cognition.intent_engine import build_intent
        from core.kernel.execution_policy_kernel import evaluate
        from payments.access_controller import check_access
        from agents.consensus import run_agents
        from llm.router import route_llm

        message = (
            update.get("message", {}).get("text")
            or update.get("edited_message", {}).get("text")
        )

        if not message:
            return {"response": "ignored"}

        intent = build_intent(message)
        decision = evaluate(intent)

        if decision == "DENY":
            return {"response": "denied"}

        wallet = update.get("message", {}).get("from", {}).get("id", "unknown")

        if not await check_access(wallet, intent):
            return {"response": "payment_required"}

        agent_output = await run_agents(intent)
        response = await route_llm(agent_output)

        return {"response": response}

    except Exception as e:
        print("HANDLE_UPDATE ERROR:", e)
        return {"response": "error"}