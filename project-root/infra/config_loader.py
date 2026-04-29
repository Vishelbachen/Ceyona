import os
from pathlib import Path


def load_env_file(path: str = ".env") -> None:
    """
    Load .env file into os.environ if not already set.
    No-op if file doesn't exist.
    pydantic-settings handles this automatically — use only for early-init needs.
    """
    env_path = Path(path)
    if not env_path.exists():
        return

    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value