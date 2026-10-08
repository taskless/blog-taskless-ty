# Runtime rule lessons

`always-truthy-typeddict-inherited` handles ty's actual TypedDict example, the one the `sg` rule can't: `x: Bar`, `Bar(Foo)`, `Foo(TypedDict)`, possibly across files.

## The shape

A runtime rule is a directory with ast-grep **captures** and one **`check.ts`**. The captures do the cheap part across the whole repo. `check.ts` gets every match from every capture in one call, each with its file, position, matched text and captured metavariables, and returns findings.

Ours has three captures: conditions on a parameter annotated with a plain class name, every class with a base list, and every `from module import ...`. `check.ts` builds a class index, resolves the annotation, walks the bases up to `TypedDict`, and tracks which keys are required (`total=False`, `Required[]`, `NotRequired[]`).

Splitting it this way kept the TypeScript small. ast-grep finds the candidates and `check.ts` only decides.

## Resolve the way a reader would

The first version fell back to "the one class with that name in the repo" when a name wasn't defined locally. In a codebase like Django, where class names repeat everywhere, that guess would go wrong, so we replaced it before running it on the corpus. The working version follows the importing file's own imports: `from app.models import Order` resolves to the `Order` in `app/models.py`, including `as` aliases and relative imports, and any other name resolves only within the same file.

A name imported from outside the repo (`from pydantic import BaseModel`), a star import, or two candidates resolves to nothing, and the check stays quiet. A wrong finding on a check like this costs more trust than a missed one.

## Fixtures are directories

The evidence spans files, so each test case is a directory and the check gets it as its root. We wrote five that must fire (the thread's example, inheritance across two files, a relative `as` import, `Required[]` in a `total=False` class, `TypedDict` imported under another name) and five that must stay quiet (all keys optional, a non-TypedDict class, an unresolvable third-party base, a same-named class in another module, every key `NotRequired`).

Every case has to fire a capture. A case where no capture matches never reaches `check.ts`, so it proves nothing about the check. Taskless reports that as a defect in the fixture.

## Check the fixtures against the real tool

We ran ty on all 10 cases. Two disagreed at first, and both were our mistakes. One fixture used `NotRequired` without importing it, so ty treated the key as required. The other used a relative import that ty couldn't resolve from inside our repo's hidden `.tests/` directory. Copied out on its own, ty agreed. After fixing the first, ty agreed with all 10.

Without that cross-check, both fixtures would have encoded a wrong idea of what correct means.

## Prove the zero

On the corpus the rule reports nothing, and so does ty. A zero could also mean the rule never ran. So we planted a two-file TypedDict bug inside Django's source tree and ran it again. It was caught, resolving the import through Django's package layout, and a full `taskless check` over Django took about 5 seconds. `uv run corpus/plant.py` reproduces it. A runtime check gets 10 seconds by default.

## Unsigned code doesn't run by default

A runtime rule executes code on the machine that runs it. Taskless only runs runtime rules its service has signed, and a rule you write yourself is never signed. So `taskless check` skips it, and both `test` and `check` need `--dangerously-run-scripts` to run it. That's why every script and the README in this repo pass the flag, and why the README asks you to read `check.ts` first.

The flag is the security model doing its job. An `sg` or Vale rule is data, and the worst a bad one can do is a wrong finding. A runtime rule is a program.

## What it still misses

It resolves names and does no type inference. A type alias (`Payload = Order`), a TypedDict built with `TypedDict("Name", {...})`, and an annotation written `app.models.Order` all resolve to nothing, so each one is a silent miss and never produces a wrong finding.
