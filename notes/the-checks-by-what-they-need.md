# The checks, by what they need

The thread shows six checks across seven screenshots: an uncalled function, the same with an `async def`, a generator, a TypedDict, a 1-element tuple, an Enum, and `isinstance` exhaustiveness. The uncalled sync and async functions are one check. Sorting them by what a tool needs to know made the line between a rule and a type checker clear. Each tier costs more than the last.

## Syntax only

A generator expression in a condition, like `if (x > 42 for x in items):`, is always true, because a generator object is truthy whether or not it would yield anything. Nothing needs resolving, so the `sg` rule matches ty on every direct use.

It misses `gen = (...)` followed by `if gen:`. Catching that means tracking what `gen` holds, which is dataflow. pylint catches it.

## The same file

Three of the checks need to know what a name refers to, and in the thread's examples the answer is in the same file:

- an uncalled function, `if condition:` where `def condition()` (or `async def`) is in the module
- an always-truthy Enum, `if choice:` where `choice: Choice` and `Choice(Enum)` defines no `__bool__` or `__len__`
- a 1-element tuple, `if self.x:` where `self.x: tuple[int]`, which ty answers with "Did you mean `tuple[int, ...]`?"

ty also flags a forgotten `await` (`if f():` where `f` is `async def`), which isn't in the thread. We added a rule for it in the same tier.

ast-grep handles these because a metavariable bound in one part of a rule has to match the same text everywhere else it's used. A rule can say "`$F` in this condition, and a `def $F` at module level," and that covers every example in the thread.

Each edge case adds a clause, though: a parameter with the same name, a local assignment with the same name. A function used above its `def` would need a third, and that one we left as a known false positive. Writing those clauses is building scope resolution by hand, and it's where the false positives came from (see [real-code-is-the-test.md](real-code-is-the-test.md)).

## The whole repository

ty's TypedDict example is `x: Bar`, `Bar(Foo)`, `Foo(TypedDict)`. Whether `if not x:` is always false depends on classes that can live in other files and inherit through each other. ast-grep sees one file and can't walk a chain, so the `sg` rule only catches a TypedDict defined directly in the same file.

Taskless runtime rules exist for evidence spread across files. See [runtime-rule-lessons.md](runtime-rule-lessons.md).

## Types

The last check is exhaustiveness: `if isinstance(x, int): ... elif isinstance(x, str): ...` with `x: int | str`. The `elif` is always true, so ty suggests an `else` with `assert_never`. Seeing that means narrowing a union across branches. It's a type checker's job, and nothing in this repo tries it. ty ships this one (`redundant-condition-strict`) switched off.
