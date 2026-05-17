async def _classify_with_model(text: str, model: str, system: str) -> bool:
    try:
        from llm.groq_client import groq_client

        # llama-prompt-guard models are text classifiers:
        # they accept ONLY a single user message — no system role allowed.
        is_guard_model = "prompt-guard" in model
        if is_guard_model:
            messages = [{"role": "user", "content": text[:2000]}]
        else:
            messages = [
                {"role": "system", "content": system},
                {"role": "user",   "content": text[:2000]},
            ]

        response = await groq_client.complete(
            model=model,
            messages=messages,
            max_tokens=5,
            temperature=0.0,
        )
        verdict = response.text.strip().upper()
        return verdict.startswith("SAFE")
    except Exception as exc:
        logger.error(
            "Safety Gate model unavailable — defaulting to DENY",
            extra={"model": model, "error": str(exc)},
        )
        return False