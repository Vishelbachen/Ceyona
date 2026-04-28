from core.kernel.execution_policy_kernel import ExecutionPolicyKernel, ExecutionContext
from llm.model_router import ModelRouter
from retrieval.retrieval_engine import RetrievalEngine


class Orchestrator:
    def __init__(self):
        self.epk = ExecutionPolicyKernel()
        self.llm = ModelRouter()
        self.retrieval = RetrievalEngine()

    def handle(self, user_id: str, message: str):
        ctx = ExecutionContext(
            user_id=user_id,
            message=message,
            estimated_cost=0.01
        )

        if not self.epk.evaluate(ctx):
            return "Request denied by EPK"

        docs = self.retrieval.search(message)
        return self.llm.generate(message, docs)