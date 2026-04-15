def refine_output(text: str) -> str:
    text = text.strip()

    # убираем markdown мусор
    if text.startswith("**") and text.endswith("**"):
        text = text[2:-2]

    return text