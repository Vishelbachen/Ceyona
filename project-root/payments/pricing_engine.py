class PricingEngine:
    """
    Converts usage into cost (v4.7 economic rules simplified)
    """

    TOKEN_RATE = 0.00001

    def calculate_cost(self, tokens: int) -> float:
        return tokens * self.TOKEN_RATE