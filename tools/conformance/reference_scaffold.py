"""Read-only adapters to the actual Python references, not a product runtime."""
import ast
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

PIN = "e96ef4939650268c216c5343f29e765db54cd047"
SOURCE_SHA = "51852a0fca8d21f59932d89769d811abbb21287921ad88bad34d8fc7f808e5ad"


def finite(raw):
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError("nonfinite JSON")
    return value


def forbidden(_):
    raise ValueError("nonfinite JSON")


def main():
    root = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(root))
    requests = json.load(sys.stdin)
    artifacts = None
    method = None
    replies = []
    for request in requests:
        try:
            value = json.loads(request["json"], parse_float=finite, parse_constant=forbidden)
        except ValueError:
            outcome = {"status": "reject"}
        else:
            if request["profile"] == "handoff":
                if method is None:
                    def git(path):
                        return subprocess.check_output(["git", "--no-replace-objects", "-C", str(root), "show", f"{PIN}:{path}"], stderr=subprocess.PIPE, timeout=10)
                    source = git("tests/test_handoff_vectors.py")
                    if hashlib.sha256(source).hexdigest() != SOURCE_SHA:
                        raise ValueError("handoff source changed")
                    cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == "HandoffVectorsTests")
                    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "valid_references")
                    scope = {}
                    exec(compile(ast.Module(body=[node], type_ignores=[]), "pinned-handoff-reference", "exec"), scope)
                    method = scope["valid_references"]
                    owner = SimpleNamespace(vectors=json.loads(git("tests/handoff_vectors.json")))
                valid = isinstance(value, list) and method(owner, value)
                outcome = {"status": "valid" if valid else "reject"}
            else:
                if artifacts is None:
                    from tools.overlay_sim.scenarios import artifacts as run
                    artifacts = run()
                name = {"overlay-csv": "scenarios.csv", "overlay-md": "SCENARIOS.md", "overlay-json": "billboards.json"}[request["profile"]]
                outcome = {"status": "bytes", "hex": artifacts[name].hex()}
        replies.append({"id": request["id"], "outcome": outcome})
    print(json.dumps(replies, separators=(",", ":")))


if __name__ == "__main__":
    main()
