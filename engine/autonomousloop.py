class AutonomousLoop:
    """
    AI can generate its own next steps (agent behavior)
    """

    def decide_next_task(self, user_input: str, memory: str):
        text = user_input.lower()

        tasks = []

        # example autonomous triggers
        if "plan" in text or "strategy" in text:
            tasks.append("breakdown_task")

        if "fix" in text or "bug" in text:
            tasks.append("debug_task")

        if "optimize" in text:
            tasks.append("optimization_task")

        return tasks