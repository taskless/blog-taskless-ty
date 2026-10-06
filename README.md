# taskless-and-ty

On 2026-09-24 Charlie Marsh [posted a thread](https://x.com/charliermarsh/status/2103199517294166518) about ty's new `redundant-condition` check, which flags conditions that are always true or always false. The classic case is `if condition:` where `condition` is a function nobody called. Those are lint-shaped bugs, so this repo rebuilds each example from the thread as a [Taskless](https://taskless.io) rule and runs both tools over the same code.

## Run it

You need [uv](https://docs.astral.sh/uv/) and Node.

```sh
uv sync
scripts/compare.sh              # ty and Taskless over examples/, side by side
scripts/compare.sh path/to/code # or over anything else
```

Run them over six real codebases (django, flask, httpx, rich, black, pydantic), each pinned to a commit in `corpus/repos.txt`:

```sh
uv run corpus/run.py            # clones into corpus/.repos/, writes corpus/results/
```

Run the rules' own tests:

```sh
npx @taskless/cli-nightly@0.12.0-20261006162512x92b3715 test .taskless/rules/sg
npx @taskless/cli-nightly@0.12.0-20261006162512x92b3715 test .taskless/rules/runtime --dangerously-run-scripts
```

Both scripts pass `--dangerously-run-scripts` to `taskless check`. The runtime rule below runs code, and Taskless only runs runtime rules its service signed. A rule written by hand never gets that signature, so without the flag `check` skips it. Read `check.ts` before you run it. That's what the flag is asking you to do.

ty is pinned to 0.0.84. The rules use the per-rule directory layout from Taskless 0.12, so for now they need the nightly CLI.

## Scorecard

Current output of `scripts/compare.sh` over `examples/`:

| Thread example | Taskless rule | Result |
| --- | --- | --- |
| `if condition:` on an uncalled function | `uncalled-function-in-condition` | Matches ty, including `while`, ternary and `and` forms |
| `if f:` on an uncalled `async def` | `uncalled-function-in-condition` | Matches ty |
| `if f():` with no `await` | `unawaited-coroutine-in-condition` | Matches ty |
| `if (x for x in xs):` | `generator-in-condition` | 3 of 4. Misses `gen = (...)` followed by `if gen:` |
| `if self.x:` where `self.x: tuple[int]` | `single-element-tuple-in-condition` | Matches ty when the annotation is in the same class |
| `if choice:` on an `Enum` | `always-truthy-enum` | Matches ty when the Enum is in the same file |
| `if not x:` on a TypedDict with required keys | `always-truthy-typeddict` (sg) | Catches `class D(TypedDict)` in the same file. Misses the thread's `Bar(Foo)`, because ast-grep can't follow inheritance |
| same | `always-truthy-typeddict-inherited` (runtime) | Matches ty, including inheritance across files, `import ... as`, relative imports, `total=False`, `Required[]` and `NotRequired[]` |
| `elif isinstance(x, str)` exhaustiveness | none | Needs union narrowing, which is a type checker's job. ty ships it off by default, and `pyproject.toml` turns it on here |

Totals: ty 15, Taskless 13, both 13. Taskless flags nothing ty doesn't.

## Real codebases

`corpus/results/` holds every line each tool flags across 4,111 Python files, one finding per line.

ty reports 28. Most are outside the thread's examples: string literals, modules, `TypeVar`s, and `tuple[()]` class attributes in Django's admin that subclasses override. Three are uncalled functions. One of those (black's test data) is the same line the Taskless rules flag. The other two need resolution a single-file rule can't do: `Field` imported from pydantic, and `Foo.bar` reassigned on a class.

The Taskless rules report 2. One is that shared black line. The other is a false positive: `foo` used on line 18 of a file whose `def foo` is on line 70. ty knows definition order and ast-grep doesn't.

## How the rules got to 2

The first draft passed every one of its own tests and flagged 23 lines across the corpus. Only one was a real bug. Each fix below is its own commit, with the test case it added and the corpus lines it removed, so `git log -p corpus/results/taskless.txt` tells the whole story.

| Commit | Change | Corpus hits |
| --- | --- | --- |
| [`first-draft`](https://github.com/theCodeDrift/taskless-and-ty/commit/c3ae703) | Six rules, all tests green | 23 |
| [`45f2bdf`](https://github.com/theCodeDrift/taskless-and-ty/commit/45f2bdf) | Match only the condition of a ternary. `enumerate_reversed if r else enumerate` was being flagged for its values | 17 |
| [`3af704e`](https://github.com/theCodeDrift/taskless-and-ty/commit/3af704e) | Count `and`/`or`/`not` only inside a condition. `convert or default_fn` is a fallback value | 16 |
| [`09a5b56`](https://github.com/theCodeDrift/taskless-and-ty/commit/09a5b56) | Skip a name a local assignment shadows. Django's `safe = isinstance(...)` sits in a module with a `safe()` function | 14 |
| [`449a683`](https://github.com/theCodeDrift/taskless-and-ty/commit/449a683) | Flag a 1-tuple only when a condition tests it. All 12 annotation hits were intentional 1-tuples | 2 |

One more commit, [`79be20c`](https://github.com/theCodeDrift/taskless-and-ty/commit/79be20c), came out of a mistake. A YAML error in one rule stopped ast-grep for every rule, and the corpus script recorded that as zero hits. Taskless reported the failure. The script wasn't checking for it. Now it does.

## Where the rules stop

Some checks are pure syntax. A generator expression in an `if` is always truthy, and the rule is as accurate as ty.

Some need same-file name resolution. ast-grep metavariables carry across `inside` and `has`, so a rule can say "this name is a function defined in this module." That covers most of the thread. Each edge case adds a clause, though: a parameter with the same name, a local assignment, a function used above its `def`.

Some need the rest of the repository. That's the TypedDict case, and it's what Taskless runtime rules are for (next section).

The rest is type inference: values flowing through variables, narrowing a union across branches, calls that return a TypedDict. That's ty's real product, and nothing in this repo tries to rebuild it.

## The runtime rule

`.taskless/rules/runtime/always-truthy-typeddict-inherited/` handles the case the `sg` rule can't. In the thread's example, `x: Bar` is tested with `if not x:`, `Bar` subclasses `Foo`, and only `Foo` subclasses `TypedDict`. The answer depends on classes that can live in other files.

A runtime rule splits the work in two:

- **Captures** are ast-grep rules that do the cheap part across the whole repository. One finds a parameter annotated with a plain class name and tested for truthiness. One finds every class with a base list. One finds every `from module import ...`.
- **`check.ts`** gets every match at once. It indexes the classes, resolves each name through the importing file's own imports (falling back to the same file), walks the bases up to `TypedDict`, and tracks which keys are required.

When a name can't be resolved to exactly one class (a third-party base, a star import, two candidates), the check reports nothing. A wrong finding costs more trust than a missed one.

Its fixtures are directories, because the evidence spans files: five that must fire (including one across two files and one through a relative `as` import) and five that must stay quiet (all keys optional, a same-named class in another module, an unresolvable third-party base). ty agrees with all ten.

Over the corpus it reports nothing, the same as ty. To prove that zero meant "ran and found nothing", a planted two-file TypedDict inside Django's tree was caught in about 4 seconds, well inside the 10-second budget a check gets.

It's still name resolution. `Payload = Order` as a type alias, a TypedDict built with the functional syntax, or a class reached through `import app.models` and used as `app.models.Order` all resolve to nothing, so they're silent misses rather than wrong answers.

## Layout

```
examples/                 thread code plus negative cases, one file per check
.taskless/rules/sg/       one directory per rule, each with a .tests/ file
.taskless/rules/runtime/  the cross-file TypedDict rule: captures/, check.ts, .tests/pass and fail
pyproject.toml            pins ty
scripts/compare.sh        the side-by-side table
corpus/run.py             the real-codebase run; repos pinned in corpus/repos.txt
corpus/results/           every finding from both tools, one per line
```
