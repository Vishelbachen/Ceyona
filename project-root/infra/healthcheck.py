from typing import Any, Dict, List, Optional


class HealthCheck:
    """
    AI Platform v4.7 — Health Check System

    RESPONSIBILITY:
    - Check availability of system components
    - Provide simple up/down status reporting
    - Serve as runtime readiness probe

    STRICT RULES:
    - No diagnostics or root cause analysis
    - No auto-healing logic
    - No LLM / retrieval / memory usage
    - No orchestration influence
    - No performance evaluation
    """

    def __init__(self):
        self._components: Dict[str, bool] = {}

    def register_component(self, name: str) -> None:
        """
        Registers a component as monitored.
        """

        self._components[name] = True

    def set_status(self, name: str, status: bool) -> None:
        """
        Updates component status.
        """

        self._components[name] = status

    def is_healthy(self, name: str) -> bool:
        """
        Returns health status of a component.
        """

        return self._components.get(name, False)

    def system_health(self) -> Dict[str, Any]:
        """
        Returns full system health snapshot.
        """

        total = len(self._components)
        healthy = sum(1 for v in self._components.values() if v)

        return {
            "total_components": total,
            "healthy_components": healthy,
            "unhealthy_components": total - healthy,
            "status": "healthy" if healthy == total else "degraded",
            "components": self._components,
        }

    def list_unhealthy(self) -> List[str]:
        """
        Returns list of failed components.
        """

        return [name for name, status in self._components.items() if not status]