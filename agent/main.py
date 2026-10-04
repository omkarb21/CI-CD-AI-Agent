import subprocess
import sys

from graph import build_graph
from nodes import log


def main() -> int:
    final = {}
    try:
        final = build_graph().invoke({}, {"recursion_limit": 50})
    finally:
        diff = subprocess.run(["git", "diff"], capture_output=True, text=True).stdout
        log("=== FINAL GIT DIFF ===")
        log(diff)
    status = final.get("status")
    log(f"=== DONE: status={status} ===")
    return 0 if status == "fixed" else 1


if __name__ == "__main__":
    sys.exit(main())
