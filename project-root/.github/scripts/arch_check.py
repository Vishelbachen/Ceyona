import os, sys

VIOLATIONS = []

for root, _, files in os.walk("app"):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)

            with open(path, encoding="utf-8") as file:
                code = file.read()

                # ❌ example rule: api should not directly touch model_decision
                if "app/api" in root and "model_decision" in code:
                    VIOLATIONS.append(f"{path} violates layer separation")

                # ❌ forbid dangerous eval usage
                if "eval(" in code:
                    VIOLATIONS.append(f"{path} uses eval() (unsafe)")

if VIOLATIONS:
    print("❌ ARCHITECTURE FAIL:")
    for v in VIOLATIONS:
        print(v)
    sys.exit(1)

print("✔ architecture OK")