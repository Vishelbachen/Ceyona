def select_model(text: str) -> str:
    text_len = len(text)

    if text_len < 50:
        return "groq/compound-mini"

    if text_len < 300:
        return "llama-3.3-70b-versatile"

    return "openai/gpt-oss-120b"