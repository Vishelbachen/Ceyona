class CallbackHandler:
    """
    Handles inline button callbacks
    """

    def handle(self, callback: dict):
        print(f"[CALLBACK] {callback}")