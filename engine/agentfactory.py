class AgentFactory:
    """
    Creates specialized AI agents dynamically
    """

    def create(self, role: str):
        if role == "research":
            return {"type": "agent", "role": "researcher"}

        if role == "coder":
            return {"type": "agent", "role": "developer"}

        if role == "analyst":
            return {"type": "agent", "role": "analyst"}

        return {"type": "agent", "role": "general"}