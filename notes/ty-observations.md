# ty observations

Things we noticed about ty 0.0.84 while using it as the reference.

## It reaches well past the thread

Across the corpus, `redundant-condition` fires 28 times. Most are outside the thread's examples: string literals, `...`, modules, `TypeVar`s, an `Annotated` special form, and empty tuples. Three are uncalled functions, all in test code. Two of those are `assert Field` and `assert Foo.bar` in pydantic's tests, and they need resolution no single-file rule can do.

One is the thread's own tuple case in a form our rule can't see: `self.geom_param_pos` in Django's GIS functions, set as a bare `geom_param_pos = (0,)` with no annotation. ty calls the condition always true, but subclasses override the attribute, and one of them sets it to `()`. So it's arguable in the same way as the empty tuples below.

## Some of its hits are arguable

Eleven are tuple attributes in Django that subclasses or later code change: the `geom_param_pos` case above, and 10 empty tuples flagged as always falsy. `list_display_links = ()`, `filter_vertical = ()` and `filter_horizontal = ()` are `ModelAdmin` defaults that admin subclasses exist to override. `_prefetch_related_lookups = ()` is set in `QuerySet.__init__`, and the same file later assigns a non-empty tuple to that attribute on a cloned queryset. ty doesn't connect the two, so it reports a condition that isn't constant in practice. A type checker's finding still needs reading.

## It skips some literal constants on purpose

ty's docs say `redundant-condition` excludes a condition that is `True`, `False` or an exact integer, so `if True:` and `while 1:` aren't flagged. A string literal or `...` is, so `if "a":` is. pylint flags all of them, and on the corpus that's most of its noise.

## It knows definition order

It doesn't flag `foo` used above `def foo`, which is our one remaining false positive.

## The strict check is off by default

`redundant-condition-strict` (the `isinstance` exhaustiveness case) has to be enabled. This repo turns it on in `pyproject.toml` for the examples and off for the corpus, so the corpus shows what a default ty user gets. Left on, it added 110 hits across the corpus.

## Where you run it from matters

Run from our repo's root, ty couldn't resolve a relative import inside a test fixture under the hidden `.tests/` directory. Copied out on its own, the same files resolved and the check fired. The corpus runs ty from inside each cloned project, so imports resolve against that project.
