class PluginSystem:
    """
    External extension layer (like OpenAI tools ecosystem)
    """

    def __init__(self):
        self.plugins = {}

    def register(self, name: str, plugin):
        self.plugins[name] = plugin

    def execute(self, name: str, input_data):
        plugin = self.plugins.get(name)
        if not plugin:
            return None
        return plugin(input_data)