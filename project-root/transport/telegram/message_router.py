class MessageRouter:
    """
    Transport layer only (no logic)
    """

    def listen(self):
        while True:
            msg = input("user> ")
            print(f"received: {msg}")