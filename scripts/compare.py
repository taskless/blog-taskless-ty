"""Run ty and Taskless over the same files and print a side-by-side table.

Usage: uv run scripts/compare.py [path ...]   (defaults to examples/)

Each row is one line that either tool flagged. A dash means that tool was silent.
"""

import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKLESS = ["npx", "-y", "@taskless/cli-nightly@0.12.0-20261006162512x92b3715"]
# The runtime rule is hand-written, so the Taskless service never signed it, and a plain
# `check` skips it. This flag runs its check.ts anyway. Read that file before you pass it.
UNSIGNED = "--dangerously-run-scripts"
TY_LINE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):\d+: \w+\[(?P<rule>[a-z-]+)\]")


def run_ty(paths):
    out = subprocess.run(
        ["uv", "run", "ty", "check", "--output-format", "concise", "--exit-zero", *paths],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    hits = defaultdict(set)
    for line in out.splitlines():
        m = TY_LINE.match(line)
        if m and m["rule"].startswith("redundant-condition"):
            hits[(m["file"], int(m["line"]))].add(m["rule"])
    return hits


def run_taskless(paths):
    out = subprocess.run(
        [*TASKLESS, "check", "--json", UNSIGNED, *paths],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    hits = defaultdict(set)
    for r in json.loads(out).get("results", []):
        hits[(r["file"], r["range"]["start"]["line"] + 1)].add(r["ruleId"])
    return hits


def main():
    paths = sys.argv[1:] or ["examples"]
    ty, tl = run_ty(paths), run_taskless(paths)
    rows = sorted(set(ty) | set(tl))
    if not rows:
        print("Neither tool flagged anything.")
        return

    cells = [(f"{f}:{n}", ", ".join(sorted(ty.get((f, n), []))) or "-",
              ", ".join(sorted(tl.get((f, n), []))) or "-") for f, n in rows]
    head = ("location", "ty", "taskless")
    widths = [max(len(c[i]) for c in [head, *cells]) for i in range(3)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*head))
    print(fmt.format(*("-" * w for w in widths)))
    for c in cells:
        print(fmt.format(*c))

    both = sum(1 for k in rows if k in ty and k in tl)
    print(f"\nty: {len(ty)}  taskless: {len(tl)}  both: {both}  "
          f"ty only: {len(set(ty) - set(tl))}  taskless only: {len(set(tl) - set(ty))}")


if __name__ == "__main__":
    main()
