from core.execution.orchestrator import Orchestrator
from transport.message_router import MessageRouter
from llm.model_router import ModelRouter
from retrieval.retrieval_engine import RetrievalEngine
from core.kernel.execution_policy_kernel import ExecutionPolicyKernel


class Application:
    def __init__(self):
        self.router = MessageRouter()
        self.orchestrator = Orchestrator()

    def run(self):
        print("v4.7 platform started")
        self.router.listen()


def bootstrap_app() -> Application:
    return Application()