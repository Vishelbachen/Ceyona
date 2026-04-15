class FeedbackLoop:
    """
    Learns from user interactions (implicit training signal)
    """

    def __init__(self):
        self.history = []

    def add_feedback(self, user_input: str, response: str, rating: int = 0):
        self.history.append({
            "input": user_input,
            "response": response,
            "rating": rating
        })

    def get_signal(self):
        if not self.history:
            return 0

        return sum(h["rating"] for h in self.history) / len(self.history)