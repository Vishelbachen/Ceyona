class RLHFSystem:
    """
    Reinforcement learning from user feedback (simplified core)
    """

    def __init__(self):
        self.dataset = []

    def add_sample(self, prompt, response, rating):
        self.dataset.append({
            "prompt": prompt,
            "response": response,
            "rating": rating
        })

    def get_training_data(self):
        return sorted(self.dataset, key=lambda x: x["rating"], reverse=True)