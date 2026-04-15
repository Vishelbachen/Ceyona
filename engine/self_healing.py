class SelfHealing:
    def analyze(self, error: str):

        if "timeout" in error:
            return "reduce_load"

        if "memory" in error:
            return "clear_cache"

        if "tool" in error:
            return "disable_tool"

        return "unknown"