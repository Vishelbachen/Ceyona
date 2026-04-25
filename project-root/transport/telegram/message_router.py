async def handle_update(update: dict):

    message = update.get("message", {}).get("text")
    if not message:
        return {"status": "ignored"}

    wallet = update.get("message", {}).get("from", {}).get("id")
    if not wallet:
        return {"status": "no_user"}

    intent = build_intent(message)

    decision = evaluate(intent)

    if decision == "DENY":
        return {"status": "denied"}

    try:
        access = await check_access(wallet, intent)
    except Exception:
        return {"status": "access_error"}

    if not access:
        return {"status": "payment_required"}

    agent_output = await run_agents(intent)

    try:
        response = await route_llm(agent_output)
    except Exception:
        return {"status": "llm_error"}

    return {"response": response}