"""
Shared fixtures and pytest configuration.
All tests are pure unit tests — no Supabase, Redis, Groq, or HuggingFace calls.
External I/O is mocked at the boundary.
"""


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (handled by pytest-asyncio)"
    )