"""Run ty, Taskless, pylint and ruff over the same files and print a side-by-side table.

Usage: uv run scripts/compare.py [path ...]   (defaults to examples/)

Each row is one line that ty, Taskless or pylint flagged as an always-true or
always-false condition. The ruff column shows anything ruff's correctness rules say
about that same line (see RUFF_SELECT in tools.py). A dash means the tool was silent.
"""

import sys
from collections import defaultdict

from tools import run_pylint, run_ruff, run_taskless, run_ty

TOOLS = {"ty": run_ty, "taskless": run_taskless, "pylint": run_pylint, "ruff": run_ruff}


def by_line(hits):
    rows = defaultdict(set)
    for h in hits:
        rows[(h.file, h.line)].add(h.rule)
    return rows


def main():
    paths = sys.argv[1:] or ["examples"]
    results = {name: by_line(run(paths)) for name, run in TOOLS.items()}
    rows = sorted(set(results["ty"]) | set(results["taskless"]) | set(results["pylint"]))
    if not rows:
        print("Nothing flagged.")
        return

    head = ("location", *TOOLS)
    cells = [(f"{f}:{n}", *(", ".join(sorted(results[t].get((f, n), []))) or "-" for t in TOOLS))
             for f, n in rows]
    widths = [max(len(c[i]) for c in [head, *cells]) for i in range(len(head))]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*head))
    print(fmt.format(*("-" * w for w in widths)))
    for c in cells:
        print(fmt.format(*c))

    ty = set(results["ty"])
    print()
    for name in TOOLS:
        flagged = set(results[name]) & set(rows)
        print(f"{name:<9} {len(flagged):>3} lines   {len(flagged & ty):>3} of ty's {len(ty)}")


if __name__ == "__main__":
    main()
