class RuntimeEnforcer:

    def check_call(self, caller, callee):
        if not self.allowed(caller, callee):
            raise ForbiddenDependency(f"{caller} -> {callee}")

    def allowed(self, caller, callee):
        return (caller, callee) in self.rules