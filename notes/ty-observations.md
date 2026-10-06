# ty observations

Things we noticed about ty 0.0.84 while using it as the reference.

## It reaches well past the thread

Across the corpus, `redundant-condition` fires 28 times. Most are outside the thread's examples: string literals, modules, `TypeVar`s, `...`, and empty tuples. Three are uncalled functions, and two of those need resolution no single-file rule can do: `Field` imported from pydantic, and `Foo.bar` reassigned on a class.

## Some of its hits are arguable

Ten are empty-tuple attributes in Django, flagged as always falsy. `list_display_links = ()`, `filter_vertical = ()` and `filter_horizontal = ()` are `ModelAdmin` defaults that admin subclasses exist to override. `_prefetch_related_lookups = ()` is set in `QuerySet.__init__` and reassigned later in the same file as `clone._prefetch_related_lookups + lookups`. ty is reasoning from the first value it saw, so the condition isn't constant in practice. A type checker's finding still needs reading.

## It skips literal constants on purpose

`if True:` and `if False:` aren't flagged, which is the right call. pylint flags them, and on the corpus that's most of its noise.

## It knows definition order

It doesn't flag `foo` used above `def foo`, which is our one remaining false positive.

## The strict check is off by default

`redundant-condition-strict` (the `isinstance` exhaustiveness case) has to be enabled. This repo turns it on in `pyproject.toml` for the examples and off for the corpus, so the corpus shows what a default ty user gets. Left on, it added 110 hits across the corpus.

## Where you run it from matters

Run from our repo's root, ty couldn't resolve a relative import inside a test fixture under the hidden `.tests/` directory. Copied out on its own, the same files resolved and the check fired. The corpus runs ty from inside each cloned project, so imports resolve against that project.
