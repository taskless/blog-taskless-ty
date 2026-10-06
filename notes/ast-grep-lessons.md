# ast-grep lessons

Things that cost time writing the `sg` rules for Python, on ast-grep 0.45.3.

## Type annotations don't parse as subscripts

In tree-sitter-python, `tuple[int]` inside an annotation is a `generic_type` with a `type_parameter` child. A pattern like `tuple[$T]` matched nothing, with no error. `--debug-query=cst` on a sample line showed the real shape.

## The condition of a ternary is the second named child

`a if cond else b` is a `conditional_expression` with three named children and no field names. `nthChild: 2` picks the condition. Matching anything inside it is what flagged black's `enumerate_reversed if is_reversed else enumerate`.

## One YAML mapping can't hold two `any:` keys

It's an easy mistake when nesting conditions, and it doesn't fail on its own. It takes down every rule in the scan. Moving the shared logic into `utils:` and referring to it with `matches:` avoided the duplicate and let two rules share it.

## A relational rule needs a positive matcher

`has: { field: type }` alone is rejected ("Rule must have one positive matcher"). It needs a `kind` or `pattern` too: `has: { field: type, kind: type }`.

## Taskless wants a `kind` next to every `regex`

`taskless verify` rejects a regex with no sibling `kind` (`sg-regex-needs-kind`), because a bare regex is tested against every node. It caught one of our rules on the first `taskless test`, and the same pattern was sitting in two more.

## Metavariables carry across relational rules

This is what makes same-file checks possible. `pattern: $F` on the condition and `has: { field: name, pattern: $F }` on a `function_definition` elsewhere in the module have to bind the same text. One rule can say "this name, and a `def` of this name."

**Walking up a chain of `and`/`or`/`not`/parens** works with `inside` plus a `stopBy` that stops at the first node outside the chain, then checking that node with `matches: condition-slot`. Without it, the rule only saw one level, and `if not (cond and other):` slipped through.

## Testing a single bad rule

Because one malformed rule stops ast-grep for every rule, always run `taskless test` (or `verify`) on a rule after editing it, before a full scan. A full scan's silence can mean the scan didn't happen.
