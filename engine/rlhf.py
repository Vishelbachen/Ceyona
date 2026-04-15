class RLHF:
    def __init__(self):
        self.dataset = []

    def add(self, prompt, response, rating):
        self.dataset.append({
            "prompt": prompt,
            "response": response,
            "rating": rating
        })

    def get_data(self):
        return sorted(self.dataset, key=lambda x: x["rating"], reverse=True)