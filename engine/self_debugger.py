class SelfDebugger:
    """
    Detects failures and suggests fixes
    """

    def analyze(self, error_log: str):
        if "timeout" in error_log:
            return "reduce_model_complexity"

        if "null" in error_log:
            return "add_fallback_checks"

        if "memory" in error_log:
            return "optimize_memory_pipeline"

        return "unknown_issue"