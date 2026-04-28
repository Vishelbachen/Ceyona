from typing import Dict, Any


class AccessController:
    """
    AI Platform v4.7 — Access Controller

    RESPONSIBILITY:
    - Validate whether user has sufficient credits for execution
    - Enforce economic constraints (TON / internal balance)
    - Act as final financial gate before execution

    STRICT RULES:
    - No pricing calculations
    - No routing decisions
    - No LLM / retrieval / memory access
    - No orchestrator interaction logic
    """

    def __init__(self, wallet_manager):
        self.wallet_manager = wallet_manager

    def check_access(
        self,
        user_id: str,
        estimated_cost: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Determines whether execution is financially allowed.
        """

        balance = self.wallet_manager.get_balance(user_id)

        required = estimated_cost.get("total_cost", 0.0)

        allowed = balance >= required

        return {
            "user_id": user_id,
            "balance": balance,
            "required": required,
            "allowed": allowed,
        }

    def enforce(self, access_result: Dict[str, Any]) -> bool:
        """
        Hard gate enforcement.
        """

        return bool(access_result.get("allowed", False))