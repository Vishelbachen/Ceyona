from dataclasses import dataclass


@dataclass
class ExecutionContext:
    user_id: str
    message: str
    estimated_cost: float


class ExecutionPolicyKernel:
    """
    Stateless EPK gate (v4.7)
    """

    def evaluate(self, ctx: ExecutionContext) -> bool:
        if ctx.estimated_cost > 0.3:
            return False
        return True