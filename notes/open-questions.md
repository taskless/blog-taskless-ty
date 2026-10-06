# Open questions

## Lead with the count or the line?

"Taskless gets 13 of ty's 15" and "here's exactly where type inference starts" are both true, and the post could open with either.

## One TypedDict rule or two?

The `sg` rule and the runtime rule both flag a TypedDict defined in the same file. Keeping both shows the two tiers side by side. Dropping the `sg` one gives one finding per bug.

## Stable CLI

The rules use Taskless 0.12's per-rule directory layout, so the repo pins a 0.12 nightly. When 0.12 ships stable, that's one line in `package.json`.

## Beyond Python

Part of the argument is that the same rule shape works in other languages. Other ecosystems have their own built-in versions of some of these checks, which fits the point that sometimes a specialized tool is the answer. Any specific claim about another language's tooling needs checking before it goes in the post, and that proof can live outside this repo.

## Checking a path outside the project

`taskless check` given a path outside the project, or one that doesn't exist, reports success with no findings. `compare.sh` refuses those paths for now. Asked upstream whether that's intended: [taskless/cli#475](https://github.com/taskless/cli/issues/475).
