# notes

What we learned building this repo: what we tried, what broke, and what it says about ty, Taskless, pylint and ruff. The top-level README says how to run things. These notes are the material for the post.

- [the-argument.md](the-argument.md) covers what the four-tool comparison adds up to: ruff can't do this, pylint can with extra effort, Taskless matches the good ty cases, and sometimes the specialized tool is the answer.
- [the-checks-by-what-they-need.md](the-checks-by-what-they-need.md) sorts the thread's six checks by what a tool has to know to catch them: syntax, the same file, the whole repo, or types.
- [real-code-is-the-test.md](real-code-is-the-test.md) is how six rules with green tests flagged 23 lines on real code, and what each of the fixes down to 2 taught.
- [ast-grep-lessons.md](ast-grep-lessons.md) holds the authoring gotchas we hit writing the `sg` rules.
- [runtime-rule-lessons.md](runtime-rule-lessons.md) covers building the cross-file TypedDict rule: how a runtime rule is shaped, how it resolves names, and how we proved a zero meant something.
- [pylint-and-ruff.md](pylint-and-ruff.md) is what the two linters a Python team already has do with these bugs.
- [ty-observations.md](ty-observations.md) records what we noticed about ty along the way, including where it's arguably wrong.
- [open-questions.md](open-questions.md) lists what's undecided.

Versions throughout: ty 0.0.84, Taskless CLI 0.12.0 (ast-grep 0.45.3), pylint 4.1.2, ruff 0.16.10. The corpus is django, flask, httpx, rich, black and pydantic at the commits in `corpus/repos.txt`, 4,111 Python files in all.
