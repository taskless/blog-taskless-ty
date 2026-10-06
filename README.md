# taskless-and-ty

On 2026-09-24 Charlie Marsh [posted a thread](https://x.com/charliermarsh/status/2103199517294166518) about ty's new `redundant-condition` check, which flags conditions that are always true or always false. The classic case is `if condition:` where `condition` is a function nobody called. Those are lint-shaped bugs, so this repo rebuilds each example from the thread as a [Taskless](https://taskless.io) rule and runs it next to ty over the same code. pylint and ruff run alongside, since they're the linters a Python team already has.

What we learned along the way, including what didn't work, is in [`notes/`](notes/).

## Run it

You need [uv](https://docs.astral.sh/uv/) and Node 22.22 or later.

```sh
uv sync
npm install
scripts/compare.sh              # ty, Taskless, pylint and ruff over examples/, side by side
scripts/compare.sh path/to/code # or over any path inside this repo
```

Run them over six real codebases (django, flask, httpx, rich, black, pydantic), each pinned to a commit in `corpus/repos.txt`:

```sh
uv run corpus/run.py            # clones into corpus/.repos/, writes corpus/results/
```

Run the rules' own tests:

```sh
npm run test:rules
```

CI (`.github/workflows/check.yml`) runs those tests and `compare.sh` on every push to `main` and every pull request, and fails if the side-by-side table differs from `examples/compare.expected.txt`.

Both scripts pass `--dangerously-run-scripts` to `taskless check`. The runtime rule below runs code, and Taskless only runs runtime rules its service signed. A rule written by hand never gets that signature, so without the flag `check` skips it. Read `check.ts` before you run it. That's what the flag is asking you to do.

ty (0.0.84), pylint (4.1.2) and ruff (0.16.10) are pinned in `pyproject.toml`. The Taskless CLI is pinned in `package.json`. The rules use the per-rule directory layout from Taskless 0.12, so for now that's the nightly build.

## Scorecard

What `scripts/compare.sh` shows over `examples/`, by thread example:

| Thread example | Taskless rule | Result |
| --- | --- | --- |
| `if condition:` on an uncalled function | `uncalled-function-in-condition` | Matches ty, including `while`, ternary and `and` forms |
| `if f:` on an uncalled `async def` | `uncalled-function-in-condition` | Matches ty |
| `if f():` with no `await` (not in the thread; ty flags it too) | `unawaited-coroutine-in-condition` | Matches ty |
| `if (x for x in xs):` | `generator-in-condition` | 3 of 4. Misses `gen = (...)` followed by `if gen:`, which pylint catches |
| `if self.x:` where `self.x: tuple[int]` | `single-element-tuple-in-condition` | Matches ty when the annotation is in the same class |
| `if choice:` on an `Enum` | `always-truthy-enum` | Matches ty when the Enum is in the same file |
| `if not x:` on a TypedDict with required keys | `always-truthy-typeddict` (sg) | Catches a TypedDict defined directly in the same file, honoring `NotRequired[]`, `Required[]` and `total=False`. Misses the thread's `Bar(Foo)`, because ast-grep can't follow inheritance |
| same | `always-truthy-typeddict-inherited` (runtime) | Matches ty, including inheritance across files, `import ... as`, relative imports, `total=False`, `Required[]` and `NotRequired[]` |
| `elif isinstance(x, str)` exhaustiveness | none | Needs union narrowing, which is a type checker's job. ty ships it off by default, and `pyproject.toml` turns it on here |

Totals: ty 15, Taskless 13, pylint 5, ruff 0. Taskless and pylint flag nothing on these examples that ty doesn't.

"Matches ty" means on these examples, which double as the rules' test cases. An outside review probed variants the examples didn't cover and found three gaps (`if not co():`, an Enum in a ternary, a TypedDict with only `NotRequired` keys). Those are fixed and now in the tests. Other variants may still differ.

## pylint and ruff

pylint has had a check for this for years: `using-constant-test` (W0125). It looks at the condition itself, with no types. It catches an uncalled function in an `if` or a ternary, and a generator expression, including the `gen = (...)` variable case the Taskless rule misses. It doesn't catch the `while` or `and` forms, a missing `await`, or anything that needs a type (Enum, TypedDict, tuple), so it gets 5 of ty's 15.

ruff never ported W0125. It does catch a few always-true shapes: `F634` flags `if (a, b):` (a tuple is always true), `F631` the same in an `assert`, and `SIM222`/`SIM223` flag `x or True` and `x and False`. None of them covers a case from the thread. To check, `compare.sh` runs ruff's correctness families (`F`, `B`, `PLE`, `PLW`, `RUF`, `ASYNC`, with preview rules on) and shows anything they say about the flagged lines. On the examples that's nothing. Across the corpus, ruff's findings on those lines are mostly about something else, like an undefined name or a mutable default argument.

That matters for the argument here. A team that lints with ruff alone gets none of the thread's checks. ty adds all of them, pylint adds a few, and a handful of Taskless rules adds most of them without changing linters.

## Real codebases

`corpus/results/` holds every finding from ty, Taskless and pylint across 4,111 Python files, one per line, plus what ruff said about those same lines.

ty reports 28. Most are outside the thread's examples: string literals, `...`, modules, `TypeVar`s, and empty-tuple attributes on Django's `ModelAdmin` and `QuerySet`. Three are uncalled functions, all in test code. One (black's formatter test data) is the same line the Taskless rules flag. The other two are `assert Field` and `assert Foo.bar` in pydantic's tests, which need resolution a single-file rule can't do. None is in code that ships, so on mature codebases these bugs are rare. The thread says Astral "found and fixed multiple bugs like this internally," which is where a check like this earns its keep: catching the next one before it merges.

The Taskless rules report 2. One is that shared black line. The other is a false positive: `foo` used on line 18 of a file whose `def foo` is on line 70. ty knows definition order, and ast-grep has no notion of it. (ruff's F821 agrees: `foo` is an undefined name there.)

pylint reports 93, and 4 of them are lines ty also flags. 86 are in black's formatter test data, mostly literal `True` and `False` conditions like `if True:`. pylint flags those, and ty deliberately skips a condition that is `True`, `False` or an integer, since those are usually on purpose. 3 are false positives in Django: `if cls.view_is_async:` reads a `@classproperty`, and without types pylint sees a function and stops there. The last 4 are in pydantic, including an `elif False:` typing idiom.

ruff's file (`corpus/results/ruff.txt`) holds what it said about the lines the other three flagged: 38 findings. Four are RUF034, a ternary whose two branches are identical. None says the condition is always true or false.

## How the rules got to 2

The first draft passed every one of its own tests and flagged 23 lines across the corpus. Only one was a line ty also flags. Each fix below is its own commit, with the test case it added and the corpus lines it removed, so `git log -p corpus/results/taskless.txt` tells the whole story.

| Commit | Change | Corpus hits |
| --- | --- | --- |
| [`first-draft`](https://github.com/theCodeDrift/taskless-and-ty/commit/c3ae703) | Six rules, all tests green | 23 |
| [`45f2bdf`](https://github.com/theCodeDrift/taskless-and-ty/commit/45f2bdf) | Match only the condition of a ternary. `enumerate_reversed if r else enumerate` was being flagged for its values | 17 |
| [`3af704e`](https://github.com/theCodeDrift/taskless-and-ty/commit/3af704e) | Count `and`/`or`/`not` only inside a condition. `convert or lam_sub` is a fallback value | 16 |
| [`09a5b56`](https://github.com/theCodeDrift/taskless-and-ty/commit/09a5b56) | Skip a name a local assignment shadows. Django's `safe = isinstance(...)` sits in a module with a `safe()` function | 14 |
| [`449a683`](https://github.com/theCodeDrift/taskless-and-ty/commit/449a683) | Flag a 1-tuple only when a condition tests it. All 12 annotation hits were intentional 1-tuples | 2 |

One more commit, [`79be20c`](https://github.com/theCodeDrift/taskless-and-ty/commit/79be20c), came out of a mistake. A YAML error in one rule stopped ast-grep for every rule, and the corpus script recorded that as zero hits. Taskless reported the failure. The script wasn't checking for it. Now it does.

## Where the rules stop

Some checks are pure syntax. A generator expression in an `if` is always truthy, and the rule matches ty on every direct use.

Some need same-file name resolution. ast-grep metavariables carry across `inside` and `has`, so a rule can say "this name is a function defined in this module." That covers most of the thread. Each edge case adds a clause, though: a parameter with the same name, a local assignment with the same name. A function used above its `def` would need another, and that's the false positive we left in.

Some need the rest of the repository. That's the TypedDict case, and it's what Taskless runtime rules are for (next section).

The rest needs more than a rule: values flowing through variables (pylint handles the simplest case), narrowing a union across branches, calls that return a TypedDict. That's ty's real product, and nothing in this repo tries to rebuild it.

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
notes/                         what we learned, tried and found, for the post
examples/                      thread code plus negative cases, one file per check
examples/compare.expected.txt  the table CI expects compare.sh to print
.taskless/rules/sg/            one directory per rule, each with a .tests/ file
.taskless/rules/runtime/       the cross-file TypedDict rule: captures/, check.ts, .tests/pass and fail
scripts/compare.sh             the side-by-side table
scripts/tools.py               how each of the four tools is run, shared by both scripts
corpus/repos.txt               the six codebases, each pinned to a commit
corpus/run.py                  the real-codebase run
corpus/results/                each tool's findings, one per line
.github/workflows/             CI: rule tests and the snapshot check
pyproject.toml                 pins ty, pylint and ruff
package.json                   pins the Taskless CLI
```
