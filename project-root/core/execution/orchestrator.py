from dataclasses import dataclass
from typing import Dict, Any, Tuple

from settings import Settings


# =========================================================
# 🧠 EP KERNEL (minimal inline version)
# =========================================================
class ExecutionPolicyKernel:

    @staticmethod
    def evaluate(cost: float) -> str:
        """
        EPK decision engine:
        - ALLOW
        - DEGRADE
        - DENY
        """

        if cost > Settings.MAX_COST_THRESHOLD:
            return "DENY"
        elif cost > Settings.MAX_COST_THRESHOLD * 0.5:
            return "DEGRADE"
        return "ALLOW"


# =========================================================
# 💰 PRICING ENGINE (minimal inline version)
# =========================================================
class PricingEngine:

    @staticmethod
    def estimate(model_tier: str, input_tokens: int, output_tokens: int) -> float:
        rates = Settings.MODEL_RATES.get(model_tier, Settings.MODEL_RATES["FAST"])

        cost = (
            input_tokens * rates["in"] +
            output_tokens * rates["out"]
        ) / 1_000_000

        return cost


# =========================================================
# 🧠 MODEL ROUTER (minimal stub)
# =========================================================
class ModelRouter:

    @staticmethod
    def route(user_input: str) -> str:
        """
        Very simple heuristic routing for now.
        Later will be replaced by intent_engine.
        """

        length = len(user_input)

        if length < 50:
            return "FAST"
        elif length < 200:
            return "GENERAL"
        return "HEAVY"


# =========================================================
# 📦 RESPONSE STRUCTURE
# =========================================================
@dataclass
class ExecutionResult:
    model: str
    decision: str
    cost: float
    response: str


# =========================================================
# 🚀 ORCHESTRATOR CORE
# =========================================================
class Orchestrator:

    def __init__(self):
        self.settings = Settings

    def _mock_llm_response(self, model: str, prompt: str) -> str:
        """
        Placeholder LLM execution layer.
        Later replaced by Groq / HF / OpenAI adapters.
        """
        return f"[{model}] ответ на: {prompt[:80]}"

    def execute(self, user_input: str) -> ExecutionResult:

        # 1. Route model
        model_tier = ModelRouter.route(user_input)

        # 2. Mock token estimation (temporary heuristic)
        input_tokens = len(user_input) // 4
        output_tokens = 120  # baseline response size

        # 3. Pricing
        cost = PricingEngine.estimate(
            model_tier,
            input_tokens,
            output_tokens
        )

        # 4. EPK decision
        decision = ExecutionPolicyKernel.evaluate(cost)

        # 5. Handle policy
        if decision == "DENY":
            return ExecutionResult(
                model=model_tier,
                decision=decision,
                cost=cost,
                response="Request denied by EPK (cost limit exceeded)"
            )

        if decision == "DEGRADE":
            output_tokens = 60  # reduce response size

        # 6. Generate response (mock LLM)
        response = self._mock_llm_response(model_tier, user_input)

        return ExecutionResult(
            model=model_tier,
            decision=decision,
            cost=cost,
            response=response
        )


# =========================================================
# 🧪 SIMPLE TEST ENTRY (optional local run)
# =========================================================
if __name__ == "__main__":
    orch = Orchestrator()

    test = orch.execute("Explain how to build a neural network step by step")

    print("MODEL:", test.model)
    print("DECISION:", test.decision)
    print("COST:", test.cost)
    print("RESPONSE:", test.response)