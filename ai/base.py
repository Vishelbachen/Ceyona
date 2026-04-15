from abc import ABC, abstractmethod


class BaseAIModel(ABC):
    """
    Unified interface for all LLM providers
    """

    @abstractmethod
    async def generate(self, prompt: str, stream: bool = False):
        pass