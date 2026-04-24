from core.cognition.intent_engine import build_intent
from core.kernel.execution_policy_kernel import evaluate
from payments.access import check_access
from agents.consensus import run_agents
from llm.router import route_llm

async def handle_update(update: dict):

    message = update["message"]["text"]

    intent = build_intent(message)

    allowed = evaluate(intent)

    if not allowed:
        return {"status": "denied"}

    if not check_access(update["message"]["from"]["id"], intent):
        return {"status": "payment_required"}

    agent_result = await run_agents(intent)

    response = await route_llm(agent_result)

    return {"response": response}