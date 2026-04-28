class ResponseSynthesizer:
    """
    Merges reasoning outputs into final response
    """

    def synthesize(self, outputs: dict) -> str:
        return "\n".join([
            f"[FAST] {outputs.get('fast_agent')}",
            f"[DEEP] {outputs.get('deep_agent')}",
            f"[CREATIVE] {outputs.get('creative_agent')}"
        ])