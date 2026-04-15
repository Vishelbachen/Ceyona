from ai.openai import OpenAIModel
from ai.mistral import MistralModel
from ai.groq import GroqModel

def get_model(message: str):
    # простая логика, можно расширить
    if len(message) > 500:
        return OpenAIModel()
    return GroqModel()