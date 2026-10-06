"""How each tool is run, shared by scripts/compare.py and corpus/run.py.

Every runner takes paths relative to `cwd` and returns Hits with paths relative to
`cwd`, 1-indexed lines and columns, so the four tools line up row for row.
"""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The Taskless CLI version is pinned in package.json. `npm install` puts it here.
TASKLESS_BIN = ROOT / "node_modules" / ".bin" / "taskless"
TASKLESS = [str(TASKLESS_BIN)]
# The runtime rule is hand-written, so the Taskless service never signed it, and a plain
# `check` skips it. This flag runs its check.ts anyway. Read that file before you pass it.
UNSIGNED = "--dangerously-run-scripts"
# Our pinned ty, pylint and ruff, whichever directory they run from.
UV_RUN = ["uv", "run", "--project", str(ROOT)]

# ruff has no port of pylint's using-constant-test, and nothing else in it targets an
# always-true condition. These are its correctness families, so the column shows whether
# ruff says anything at all about the lines the other tools flag. RUF050 (empty `if`)
# is ignored because it only fires on the `pass` bodies the examples use.
RUFF_SELECT = "F,B,PLE,PLW,RUF,ASYNC"
RUFF_IGNORE = "RUF050"


@dataclass(frozen=True)
class Hit:
    file: str
    line: int
    column: int
    rule: str
    message: str = ""


def _run(argv, cwd):
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True)


TY_LINE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+): \w+\[(?P<rule>redundant-condition[a-z-]*)\] (?P<msg>.*)$")


def run_ty(paths, cwd=ROOT, strict=True):
    """ty's redundant-condition checks. `strict=False` leaves the strict variant at ty's default (off)."""
    extra = [] if strict else ["--ignore", "redundant-condition-strict"]
    out = _run([*UV_RUN, "ty", "check", "--output-format", "concise", "--exit-zero", *extra, *paths], cwd).stdout
    return [Hit(m["file"], int(m["line"]), int(m["col"]), m["rule"], m["msg"])
            for m in map(TY_LINE.match, out.splitlines()) if m]


def run_taskless(paths, cwd=ROOT):
    if not TASKLESS_BIN.exists():
        sys.exit("Taskless CLI not installed. Run `npm install` first.")
    proc = _run([*TASKLESS, "check", "--json", UNSIGNED, *paths], cwd)
    # One malformed rule stops ast-grep for every rule, and that reads as zero findings.
    # Refuse a scan that didn't run rather than report an empty result.
    report = json.loads(proc.stdout or "{}")
    if not report.get("success"):
        sys.exit(f"taskless check failed:\n{proc.stdout or proc.stderr}")
    return [Hit(r["file"], r["range"]["start"]["line"] + 1, r["range"]["start"]["column"] + 1,
                r["ruleId"], r["message"]) for r in report.get("results", [])]


PYLINT_LINE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+): (?P<rule>[a-z-]+) (?P<msg>.*)$")


def run_pylint(paths, cwd=ROOT):
    """pylint's using-constant-test (W0125), with the target's own pylint config ignored."""
    out = _run([*UV_RUN, "pylint", "--rcfile", str(ROOT / "scripts" / "empty.pylintrc"),
                "--disable=all", "--enable=using-constant-test", "--jobs=0", "--exit-zero",
                "--score=n", "--msg-template={path}:{line}:{column}: {symbol} {msg}", *paths], cwd).stdout
    # pylint columns are 0-indexed. It also reports syntax errors and unknown-option
    # warnings even with every check disabled, so keep only the check we asked for.
    return [Hit(m["file"], int(m["line"]), int(m["col"]) + 1, m["rule"], m["msg"])
            for m in map(PYLINT_LINE.match, out.splitlines()) if m and m["rule"] == "using-constant-test"]


def run_ruff(paths, cwd=ROOT):
    out = _run([*UV_RUN, "ruff", "check", "--isolated", "--no-cache", "--preview", "--exit-zero",
                "--select", RUFF_SELECT, "--ignore", RUFF_IGNORE, "--output-format", "json", *paths], cwd).stdout
    base = Path(cwd).resolve()
    # A finding with no code is a syntax error, e.g. black's deliberately invalid test data.
    return [Hit(os.path.relpath(Path(r["filename"]).resolve(), base), r["location"]["row"],
                r["location"]["column"], r["code"], r["message"]) for r in json.loads(out or "[]") if r["code"]]
