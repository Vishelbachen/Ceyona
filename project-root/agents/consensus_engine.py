class ConsensusEngine:
    """
    Merges multiple agent outputs into final decision
    """

    def merge(self, outputs: list[str]) -> str:
        return "\n".join(outputs)