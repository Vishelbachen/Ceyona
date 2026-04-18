import os
from groq import Groq


def list_models():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    models = client.models.list()

    print("\n=== AVAILABLE GROQ MODELS ===\n")

    data = getattr(models, "data", models)

    for m in data:
        print(f"- {m.id}")

    print("\n=============================\n")


if __name__ == "__main__":
    list_models()