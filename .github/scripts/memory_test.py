import sys

def test_memory_import():
    try:
        from app.memory.session_store import SessionStore
        store = SessionStore()
    except Exception as e:
        print("❌ memory layer broken:", e)
        sys.exit(1)

def run():
    test_memory_import()
    print("✔ memory system OK")

if __name__ == "__main__":
    run()