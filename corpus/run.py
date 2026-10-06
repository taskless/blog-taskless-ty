"""Run ty and the Taskless rules over real codebases and save what each one flags.

Usage: uv run corpus/run.py [--skip-ty] [name ...]   (defaults to every repo in repos.txt)

Repos are shallow-cloned at their pinned commit into corpus/.repos/ (gitignored).
Results land in corpus/results/, one line per finding, sorted, so a rule change
shows up as a plain diff of those files.
"""

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
REPOS = CORPUS / ".repos"
RESULTS = CORPUS / "results"
TASKLESS = ["npx", "-y", "@taskless/cli-nightly@0.12.0-20261006162512x92b3715"]
# The runtime rule is hand-written, so the Taskless service never signed it, and a plain
# `check` skips it. This flag runs its check.ts anyway. Read that file before you pass it.
UNSIGNED = "--dangerously-run-scripts"
TY_LINE = re.compile(r"^(?P<loc>[^:]+:\d+:\d+): \w+\[(?P<rule>redundant-condition[a-z-]*)\] (?P<msg>.*)$")


def read_repos():
    repos = []
    for line in (CORPUS / "repos.txt").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            name, url, sha = line.split()
            repos.append((name, url, sha))
    return repos


def checkout(name, url, sha):
    dest = REPOS / name
    if (dest / ".git").exists():
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=dest, capture_output=True, text=True).stdout.strip()
        if head == sha:
            return dest
    dest.mkdir(parents=True, exist_ok=True)
    git = lambda *a: subprocess.run(["git", *a], cwd=dest, check=True, capture_output=True)
    if not (dest / ".git").exists():
        git("init", "-q")
        git("remote", "add", "origin", url)
    print(f"  fetching {name}@{sha[:8]}", file=sys.stderr)
    git("fetch", "-q", "--depth", "1", "origin", sha)
    git("checkout", "-q", "--force", "FETCH_HEAD")
    return dest


def run_taskless(name):
    proc = subprocess.run(
        [*TASKLESS, "check", "--json", UNSIGNED, f"corpus/.repos/{name}"],
        cwd=ROOT, capture_output=True, text=True,
    )
    # One malformed rule stops ast-grep for every rule, and that reads as zero findings.
    # Refuse to record a scan that didn't run, rather than saving an empty result.
    report = json.loads(proc.stdout or "{}")
    if not report.get("success"):
        sys.exit(f"taskless check failed on {name}:\n{proc.stdout or proc.stderr}")
    prefix = f"corpus/.repos/{name}/"
    rows = []
    for r in report.get("results", []):
        start = r["range"]["start"]
        path = r["file"].removeprefix(prefix)
        rows.append(f"{name}/{path}:{start['line'] + 1}:{start['column'] + 1}  {r['ruleId']}")
    return rows


def run_ty(name, dest):
    # Run from inside the repo with our pinned ty. The strict variant is off by default in
    # ty and only switched on in this repo's pyproject for the examples, so ignore it here.
    out = subprocess.run(
        ["uv", "run", "--project", str(ROOT), "ty", "check", "--output-format", "concise",
         "--exit-zero", "--ignore", "redundant-condition-strict", "."],
        cwd=dest, capture_output=True, text=True,
    ).stdout
    rows = []
    for line in out.splitlines():
        m = TY_LINE.match(line)
        if m:
            rows.append(f"{name}/{m['loc']}  {m['rule']}  {m['msg']}")
    return rows


def write(kind, names, rows):
    """Replace only the given repos' lines, so a partial run keeps the others."""
    path = RESULTS / f"{kind}.txt"
    kept = [l for l in path.read_text().splitlines() if l.split("/", 1)[0] not in names] if path.exists() else []
    path.write_text("".join(f"{l}\n" for l in sorted(kept + rows)))


def main():
    args = sys.argv[1:]
    skip_ty = "--skip-ty" in args
    wanted = [a for a in args if not a.startswith("--")]
    repos = [r for r in read_repos() if not wanted or r[0] in wanted]
    RESULTS.mkdir(parents=True, exist_ok=True)

    taskless_rows, ty_rows = [], []
    for name, url, sha in repos:
        dest = checkout(name, url, sha)
        print(f"  scanning {name}", file=sys.stderr)
        taskless_rows += run_taskless(name)
        if not skip_ty:
            ty_rows += run_ty(name, dest)

    names = {r[0] for r in repos}
    write("taskless", names, taskless_rows)
    if not skip_ty:
        write("ty", names, ty_rows)

    for kind in ["taskless", "ty"]:
        lines = (RESULTS / f"{kind}.txt").read_text().splitlines()
        rules = Counter(l.split()[1] for l in lines)
        detail = ", ".join(f"{r} {n}" for r, n in sorted(rules.items()))
        print(f"{kind}: {len(lines)} ({detail})" if lines else f"{kind}: 0")


if __name__ == "__main__":
    main()
