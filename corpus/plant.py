"""Plant a two-file TypedDict bug inside Django's tree and check the runtime rule finds it.

Usage: uv run corpus/plant.py   (after `uv run corpus/run.py django` has cloned Django)

Over the corpus the runtime rule reports nothing, and so does ty. A zero could also mean
the rule never ran. This puts a TypedDict in one Django module and a truthiness test of
its subclass in another, imported through Django's package path, runs Taskless over the
whole tree, then removes both files. It exits non-zero unless the planted line is the
one reported.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from tools import run_taskless  # noqa: E402

DJANGO = ROOT / "corpus" / ".repos" / "django"
RULE = "always-truthy-typeddict-inherited"

BASE = DJANGO / "django" / "utils" / "planted_base.py"
USE = DJANGO / "django" / "contrib" / "planted_use.py"
FILES = {
    BASE: "from typing import TypedDict\n\n\nclass Foo(TypedDict):\n    X: int\n",
    USE: (
        "from django.utils.planted_base import Foo\n\n\n"
        "class Bar(Foo):\n    Y: int\n\n\n"
        "def check(x: Bar):\n    if not x:\n        print(\"empty dictionary\")\n"
    ),
}
EXPECTED = ("corpus/.repos/django/django/contrib/planted_use.py", 9)


def main():
    if not DJANGO.exists():
        sys.exit("Django isn't cloned. Run `uv run corpus/run.py django` first.")
    for path, text in FILES.items():
        path.write_text(text)
    try:
        start = time.monotonic()
        hits = [h for h in run_taskless(["corpus/.repos/django"]) if h.rule == RULE]
        elapsed = time.monotonic() - start
    finally:
        for path in FILES:
            path.unlink(missing_ok=True)

    for h in hits:
        print(f"{h.file}:{h.line}  {h.rule}")
    print(f"taskless check over Django took {elapsed:.1f}s")
    if [(h.file, h.line) for h in hits] != [EXPECTED]:
        sys.exit(f"expected exactly one {RULE} hit at {EXPECTED[0]}:{EXPECTED[1]}")


if __name__ == "__main__":
    main()
