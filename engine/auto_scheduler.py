class AutoScheduler:
    """
    AI schedules its own background tasks
    """

    def generate_tasks(self, input_text: str):
        tasks = []

        text = input_text.lower()

        if "optimize" in text:
            tasks.append("optimize_memory")

        if "monitor" in text:
            tasks.append("system_health_check")

        if "learn" in text:
            tasks.append("memory_reinforcement")

        return tasks