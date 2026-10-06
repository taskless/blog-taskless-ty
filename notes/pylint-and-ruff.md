# pylint and ruff

The two linters a Python team most likely already runs.

## pylint

`using-constant-test` (W0125) flags a condition whose value it can tell from the code alone. On the thread's examples it catches 5 of ty's 15:

- an uncalled function in an `if` or a ternary
- a generator expression in an `if`, including `gen = (...)` then `if gen:`, which our `sg` rule misses

It misses the `while` and `and` forms, a missing `await`, and anything that needs a type (Enum, TypedDict, tuple).

Across the corpus it flags 93 lines, 4 of them lines ty flags too:

- 86 are in black's formatter test data, mostly literal `True` and `False` conditions (`if True:`, `if False:`, `x if True else y`). pylint flags a literal constant. ty deliberately doesn't, since those are usually on purpose.
- 3 are false positives in Django, where `if cls.view_is_async:` reads `view_is_async`, which is a `@classproperty`. Without types, pylint sees a function definition and stops there. ty gets these right.
- 4 are in pydantic, including an intentional `elif False:` typing idiom.

pylint does support custom checkers, written in Python against its AST library (astroid). So pylint can go further than W0125. Someone has to write and maintain that checker.

Two practical notes from running it: pylint reports syntax errors and unknown-option warnings even with every check disabled, so the scripts keep only W0125. It also reads a project's own `pylintrc`, so the scripts point it at an empty one. It's the slowest of the four tools here, about 2 of the roughly 2.5 minutes a full corpus run takes.

## ruff

Ruff can't take a custom rule. Its [FAQ](https://docs.astral.sh/ruff/faq/) says it "implements all rules natively and does not support custom or third-party rules." A plugin system is described as "within-scope", but it doesn't exist yet. Ruff also never ported pylint's W0125.

It does have rules for a few other always-true shapes: `F634` (`if (a, b):`, a tuple is always true), `F631` (the same in an `assert`), `SIM222`/`SIM223` (`x or True`, `x and False`), and `PLW0129` (asserting on an empty string). None of them covers a case from the thread.

To be sure nothing in ruff covers this anyway, the scripts run its correctness families (`F`, `B`, `PLE`, `PLW`, `RUF`, `ASYNC`) with preview rules on, and report anything they say about the lines the other tools flag.

- On the examples, nothing. The only ruff finding on those lines was RUF050 ("empty `if`"), which fires because the examples use `pass` bodies, so it's ignored.
- Across the corpus, 38 findings on flagged lines. Four are RUF034, a ternary whose two branches are identical, which is about the conditional but not about whether the condition is constant. Most of the rest are mutable default arguments (B006) and useless expressions (B018) on pylint's literal-constant lines. One is useful: F821 flags `foo` as undefined on the line our rule wrongly flags (see [real-code-is-the-test.md](real-code-is-the-test.md)).

For a ruff user, "write a rule" means "turn on a rule that exists." For the thread's checks, none does.
