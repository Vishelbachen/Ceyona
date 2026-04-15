class VectorDB:
    def __init__(self):
        self.data = []

    def add(self, vector, payload):
        self.data.append({"v": vector, "p": payload})

    def search(self, vector, top_k=5):
        return self.data[:top_k]