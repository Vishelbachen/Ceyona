class SelfHealingSystem:
    """
    Detects system issues and triggers recovery actions
    """

    def analyze_failure(self, error: str):

        if "timeout" in error:
            return "reduce_model_load"

        if "memory" in error:
            return "clear_context_cache"

        if "tool" in error:
            return "disable_tool_chain"

        return "unknown_recovery"