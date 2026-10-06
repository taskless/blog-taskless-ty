# The argument

Charlie Marsh's [thread](https://x.com/charliermarsh/status/2103199517294166518) shows ty catching conditions that are always true or always false. The classic is `if condition:` where `condition` is a function nobody called. Those bugs are real and they're common. The question this repo asks is who else can catch them.

On the thread's examples (`scripts/compare.sh`):

| Tool | Lines flagged | Of ty's 15 |
| --- | --- | --- |
| ty | 15 | 15 |
| Taskless | 13 | 13 |
| pylint | 5 | 5 |
| ruff | 0 | 0 |

Four claims come out of that, each backed by something in this repo.

## Ruff can't do it

Ruff has no way to add a rule. Its [FAQ](https://docs.astral.sh/ruff/faq/) says it "implements all rules natively and does not support custom or third-party rules", and that a plugin system is "within-scope" but not built. For a ruff user, adding a rule means turning on one that already exists.

None of the existing ones cover this. With every correctness family enabled, preview rules included, ruff says nothing about any of the 15 lines. See [pylint-and-ruff.md](pylint-and-ruff.md).

A team that lints with ruff alone has no coverage for this class of bug until it adopts ty.

## pylint can, with extra effort

pylint has had `using-constant-test` (W0125) for years. With no type information it gets 5 of ty's 15. Anything past that means writing a custom checker in Python against pylint's AST library. That's possible, and it's real work.

On real code it's also noisy: 93 hits across the corpus, 4 of them on lines ty flags too.

## Taskless matches the good ty cases

Six `sg` rules and one runtime rule get 13 of ty's 15, with no false positives on the examples and 2 lines flagged across the corpus. They're YAML plus one TypeScript file, each with its own tests, and they run next to ruff without anyone switching linters.

The same rule shape works in any language ast-grep parses, and in prose through Vale. ty is a Python type checker. Taskless covers this check in Python today, and the next one in TypeScript, Go or a style guide.

## Sometimes the specialized tool is the answer

The two lines Taskless misses are a generator assigned to a variable first (dataflow), and the `isinstance` exhaustiveness check (union narrowing). Those are type inference, which is what ty is built for. The post should say so plainly. Knowing where a rule stops is part of why the rest of it can be trusted.
