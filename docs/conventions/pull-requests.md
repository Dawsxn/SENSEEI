# Pull requests

Every change reaches `develop` or `main` through a PR. There are no direct
pushes to either.

## PR titles matter more than commit messages

PRs are squash-merged into `develop`, which means **the PR title becomes the
commit message**. It is the thing that shows up in `develop`'s history forever,
so it is the thing we validate in CI.

Format is [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>
```

**Types** — same set as branch prefixes:

| Type | Use for |
| --- | --- |
| `feat` | A new capability a user or another component can observe |
| `fix` | A bug fix |
| `refactor` | Restructuring with no behaviour change |
| `chore` | Tooling, config, dependencies, housekeeping |
| `docs` | Documentation only |
| `test` | Tests only |

**Scopes** — optional but preferred. Use the part of the system the change
touches:

`api`, `session`, `analytics`, `orchestrator`, `agent`, `ui`, `db`, `eval`

**Subject** — imperative mood, lowercase, no trailing period, under ~72
characters including the prefix.

```
feat(session): add retry handling to the submit endpoint
fix(orchestrator): count attempts per step instead of per session
refactor(api): extract reading lookup into a shared dependency
chore: pin the LLM provider SDK version
docs: document the class join-code flow
```

Bad titles, and why:

```
Update stuff                      no type, says nothing
feat: Added retry handling.       past tense, capitalised, trailing period
feat(session): fix bug            type says feature, subject says fix
```

## Description

The template gives you five sections. Three are required and CI will fail the PR
if they are missing or empty:

- **Summary** — one to three sentences: what this does and why
- **Changes** — the key pieces added or changed, one bullet each
- **How to test** — the steps a reviewer follows to verify it works

Two are optional. Delete them when they do not apply:

- **Screenshots** — UI changes only. Before and after if you are replacing
  something.
- **Notes & caveats** — follow-ups, known limitations, anything a reviewer
  should watch for

Write the description for someone who has not been following your branch.

## Review

- Target `develop` unless it is a `hotfix/*`, which targets `main`
- One approval required before merge
- CI must be green
- Address comments by pushing more commits; do not force-push once review has
  started, since it makes the reviewer lose their place

## Merging

Squash merge into `develop`. Confirm the commit message field shows your **PR
title**, not a commit subject, then delete the branch.

> The repository is configured so squash merges default to the PR title. If you
> ever see a raw commit subject there instead, stop and fix it — that setting has
> drifted, and unprefixed commit messages will start leaking into `develop`.

## Releases

Releasing is a PR from `develop` into `main`, merged as a **regular merge**, not
a squash. Title it:

```
chore(release): <what is going out>
```

The regular merge keeps one commit per feature visible in `main`'s history.
Squashing would collapse the whole release into a single commit.

## Skills

If you are working with Claude Code in this repo:

- `/start-branch` — creates a correctly named branch off an up-to-date `develop`
- `/create-pr` — drafts the title and description from your actual diff, shows
  them to you, and opens the PR once you confirm

Both are conveniences. The conventions above are the source of truth, and CI is
what actually enforces them.
