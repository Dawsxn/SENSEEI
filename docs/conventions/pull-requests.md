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

The template gives you five sections. Two are required, and CI will fail the PR
if they are missing or empty:

- **Summary**: what this PR does
- **Changes**: the key pieces added or changed, one bullet each

Three are optional. Delete the heading entirely when it does not apply:

- **How to test**: the steps a reviewer follows to verify it works. Include it
  when there is something to run or click. Skip it for documentation, config,
  and anything with nothing to execute.
- **Screenshots**: UI changes only. Before and after if you are replacing
  something.
- **Notes & caveats**: one line each, a few at most.

Write the description for someone who has not been following your branch.

### Keeping notes and caveats short

A caveat earns its place only if it changes what a reviewer does or watches for.
One line each. No hedging, no restating what is already in **Changes**, no
recounting everything you considered.

```
The attempt limit of 3 is provisional.                                  good
Charts are stubbed; the real query lands next PR.                       good

It is worth noting that the attempt limit of 3 was chosen provisionally  no
and may need revisiting once we have more data, though nothing
currently depends on it either way.
```

If there is nothing that fits, delete the section. An empty-but-present caveats
list reads as though something is being withheld.

### Writing the summary

Lead with what the PR does. First sentence, present tense, the change itself:

```
Adds retry handling to the submit endpoint.
Fixes attempts being counted per session instead of per step.
Moves the Assessment Agent into a shared package.
```

Not this:

```
Currently the submit endpoint has no way of knowing how many attempts a
student has made, which means...

This PR is part of the ongoing effort to...
```

Add a second sentence of why only when the reason is not obvious from the change
itself. Two sentences is usually the whole summary. If it is running long, the
detail belongs in **Changes**.

### Do not reference the thesis manuscript

The manuscript is not in this repository. A reviewer reading the PR cannot follow
a pointer to a section, table, or figure in it, so the reference costs them
something and gives nothing back.

State the decision or the behaviour directly:

```
Sessions cannot be resumed once abandoned.          good
Sessions cannot be resumed, per section 4.3.1.      no
```

Repository documentation may cite the manuscript, since it is a reference that
outlives any one change. Pull requests may not.

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
