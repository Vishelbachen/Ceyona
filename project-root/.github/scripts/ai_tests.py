import sys

def test_orchestrator_exists():
    try:
        from app.core.orchestrator import orchestrate
    except Exception as e:
        print("❌ orchestrator import failed:", e)
        sys.exit(1)

def test_model_decision_exists():
    try:
        from app.core.model_decision import resolve_model
    except Exception as e:
        print("❌ model_decision broken:", e)
        sys.exit(1)

def run():
    test_orchestrator_exists()
    test_model_decision_exists()
    print("✔ AI pipeline structure OK")

if __name__ == "__main__":
    run()