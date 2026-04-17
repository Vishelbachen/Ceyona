class PhysicsVerifier:
    def check(self, text: str) -> bool:
        text = text.lower()

        # грубые физические red flags
        if "sin(theta) = g / r" in text:
            return False

        if "cos(theta) = g / r" in text:
            return False

        if "v = r * tan(theta)" in text:
            return False

        return True