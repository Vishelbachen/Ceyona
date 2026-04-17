PROJECT_STATE = {
    "name": "Ceyona",
    "version": "v2",
    "mode": "production",
    "capabilities": [
        "groq",
        "gemini",
        "supabase memory",
        "telegram bot",
        "fastapi webhook"
    ]
}


def get_project_memory():
    return [{
        "file": "system",
        "action": "state",
        "content": str(PROJECT_STATE)
    }]