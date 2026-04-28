from app.bootstrap import build_container


def handle_request(container, user_input: str) -> dict:
    """
    Minimal request pipeline (stub execution flow).
    Will be replaced by orchestrator later.
    """

    # TEMP: mock response (LLM layer not connected yet)
    return {
        "input": user_input,
        "output": f"[stub response] processed: {user_input}",
        "status": "ok"
    }


def main():
    container = build_container()

    # simple test flow
    while True:
        user_input = input(">>> ")

        if user_input.lower() in ["exit", "quit"]:
            break

        result = handle_request(container, user_input)
        print(result["output"])


if __name__ == "__main__":
    main()