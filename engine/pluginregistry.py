class PluginRegistry:
    """
    Dynamic tool system (like OpenAI tools / LangChain plugins)
    """

    def __init__(self):
        self.plugins = {}

    def register(self, name: str, func):
        self.plugins[name] = func

    def get(self, name: str):
        return self.plugins.get(name)

    def list(self):
        return list(self.plugins.keys())