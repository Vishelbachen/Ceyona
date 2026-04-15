class PluginRuntime:
    def __init__(self):
        self.plugins = {}

    def register(self, name, fn):
        self.plugins[name] = fn

    def run(self, name, data):
        if name not in self.plugins:
            return None
        return self.plugins[name](data)