"""Run ty, the Taskless rules, pylint and ruff over real codebases and save what each flags.

Usage: uv run corpus/run.py [--tools ty,taskless,pylint,ruff] [name ...]
       (defaults to every tool, and every repo in repos.txt)

Repos are shallow-cloned at their pinned commit into corpus/.repos/ (gitignored).
Results land in corpus/results/<tool>.txt, one line per finding, sorted, so a rule
change shows up as a plain diff of those files.

ruff has no always-true-condition rule, so ruff.txt is not a ruff scan of the whole
repo. It holds what ruff's correctness rules say about the lines the other three
tools flag, which is how the post can say whether ruff noticed anything there.
"""

import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from tools import run_pylint, run_ruff, run_taskless, run_ty  # noqa: E402

CORPUS = ROOT / "corpus"
REPOS = CORPUS / ".repos"
RESULTS = CORPUS / "results"
ALL_TOOLS = ["ty", "taskless", "pylint", "ruff"]


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


def scan(tool, name, dest, flagged):
    """One tool over one repo, as result lines prefixed with the repo name."""
    if tool == "taskless":
        # Taskless runs from this repo so it uses our .taskless/ rules.
        prefix = f"corpus/.repos/{name}/"
        return [f"{name}/{h.file.removeprefix(prefix)}:{h.line}:{h.column}  {h.rule}"
                for h in run_taskless([prefix.rstrip("/")])]
    if tool == "ty":
        # Strict is only switched on for the examples. Here ty runs at its defaults.
        hits = run_ty(["."], cwd=dest, strict=False)
    elif tool == "pylint":
        hits = run_pylint(["."], cwd=dest)
    else:
        hits = [h for h in run_ruff(["."], cwd=dest) if (h.file, h.line) in flagged]
    return [f"{name}/{h.file}:{h.line}:{h.column}  {h.rule}  {h.message}" for h in hits]


def flagged_lines(name):
    """(file, line) pairs any of ty, taskless or pylint flagged in this repo, from saved results."""
    lines = set()
    for tool in ["ty", "taskless", "pylint"]:
        path = RESULTS / f"{tool}.txt"
        for row in path.read_text().splitlines() if path.exists() else []:
            repo, rest = row.split("/", 1)
            if repo == name:
                file, line, _ = rest.split()[0].rsplit(":", 2)
                lines.add((file, int(line)))
    return lines


def write(kind, names, rows):
    """Replace only the given repos' lines, so a partial run keeps the others."""
    path = RESULTS / f"{kind}.txt"
    kept = [l for l in path.read_text().splitlines() if l.split("/", 1)[0] not in names] if path.exists() else []
    path.write_text("".join(f"{l}\n" for l in sorted(kept + rows)))


def main():
    args = sys.argv[1:]
    tools = ALL_TOOLS
    if "--tools" in args:
        k = args.index("--tools")
        tools = [t for t in ALL_TOOLS if t in args[k + 1].split(",")]
        del args[k:k + 2]
    repos = [r for r in read_repos() if not args or r[0] in args]
    names = {r[0] for r in repos}
    RESULTS.mkdir(parents=True, exist_ok=True)

    dests = {}
    for name, url, sha in repos:
        dests[name] = checkout(name, url, sha)
    # ruff goes last: it reports on the lines the other tools' saved results flag.
    for tool in tools:
        rows = []
        for name in sorted(names):
            print(f"  {tool}: {name}", file=sys.stderr)
            flagged = flagged_lines(name) if tool == "ruff" else set()
            rows += scan(tool, name, dests[name], flagged)
        write(tool, names, rows)

    for tool in ALL_TOOLS:
        path = RESULTS / f"{tool}.txt"
        lines = path.read_text().splitlines() if path.exists() else []
        rules = Counter(l.split()[1] for l in lines)
        detail = ", ".join(f"{r} {n}" for r, n in sorted(rules.items()))
        print(f"{tool}: {len(lines)}" + (f" ({detail})" if lines else ""))


if __name__ == "__main__":
    main()
