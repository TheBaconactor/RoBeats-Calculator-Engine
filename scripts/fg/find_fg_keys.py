import os
from pathlib import Path

base = str(Path(__file__).resolve().parents[2])
for root, dirs, files in os.walk(base):
    # Skip __pycache__ and .git
    dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "node_modules", ".venv"]]
    for f in files:
        if f.endswith(".py"):
            fp = os.path.join(root, f)
            try:
                with open(fp, "rb") as fh:
                    content = fh.read()
                    if b"variant_applied" in content:
                        print(f"variant_applied: {fp}")
                    if b'"finder"' in content or b"'finder'" in content:
                        print(f"finder: {fp}")
                    if b"center_ff" in content:
                        print(f"center_ff: {fp}")
            except Exception as e:
                pass
