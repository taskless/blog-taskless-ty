# Real code is the test

The first draft of the rules passed every one of its own tests. Run over six real codebases, it flagged 23 lines. One was a bug ty also reports. The other 22 were false positives.

Fixtures prove a rule does what its author imagined. A corpus proves what it does to code nobody wrote for it. Each fix below is its own commit, with the test case it added and the corpus lines it removed.

| Commit | What was wrong | Hits after |
| --- | --- | --- |
| `c3ae703` (tag `first-draft`) | | 23 |
| `45f2bdf` | The rule matched any name inside a ternary, so `enumerate_reversed if is_reversed else enumerate` in black was flagged for its *values*. Only the middle operand is a condition | 17 |
| `3af704e` | `self.convert = convert or lam_sub` is a fallback value. `and`/`or`/`not` now count only when the chain ends in a condition | 16 |
| `09a5b56` | Django's `safe = isinstance(value, SafeData)` then `if safe:` sits in a module that also defines a `safe` function. The local wins at runtime, and now in the rule | 14 |
| `449a683` | The first tuple rule flagged every `tuple[X]` annotation. All 12 corpus hits were intentional: formatter fixtures, `tuple[Unpack[...]]`, a real 1-tuple from `__reduce__`. A 1-tuple is often intentional. The bug is testing one for emptiness, which is where ty reports it | 2 |

## The two that are left

One is real: `bar=a if foo else b` in black's test data, where `foo` is a function. ty flags the same line.

The other is a false positive we kept on purpose. `foo` is used on line 18 of a file whose `def foo` is on line 70. At runtime that line raises `NameError` before the condition is ever tested. ty knows definition order, and ast-grep has no notion of it. ruff's F821 (undefined name) flags the same line, which confirms what's actually wrong there.

## The fix that came from a mistake

While making the second fix, a YAML error (a duplicated `any:` key) went into one rule. ast-grep refuses the whole config when one rule is malformed, so every rule stopped. The corpus script saved that as zero hits.

Taskless had reported the failure (`"success": false`, with the parse error). The script wasn't reading it. Commit `79be20c` makes it stop instead of saving an empty result.

A checker that reports zero when it didn't run is worse than one that crashes. The same idea drove how we tested the runtime rule (see [runtime-rule-lessons.md](runtime-rule-lessons.md)).
