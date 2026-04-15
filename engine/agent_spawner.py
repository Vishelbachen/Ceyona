class AgentSpawner:
    """
    Creates specialized sub-agents dynamically
    """

    def spawn(self, task_type: str):
        if task_type == "research":
            return "research_agent"

        if task_type == "debug":
            return "debug_agent"

        if task_type == "planning":
            return "planner_agent"

        return "general_agent"