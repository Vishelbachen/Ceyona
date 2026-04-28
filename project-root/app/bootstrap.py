from app.settings import Settings


class Container:
    """
    Lightweight dependency container (no logic, only wiring).
    """

    def __init__(self, settings: Settings):
        self.settings = settings

        # placeholders for later layers
        self.model_router = None
        self.orchestrator = None
        self.epk = None
        self.pricing_engine = None


def build_container() -> Container:
    """
    Entry DI factory.
    """
    settings = Settings()
    container = Container(settings=settings)

    return container