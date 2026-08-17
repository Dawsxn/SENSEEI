# Git workflow

## Branches

| Branch | Role | Receives from |
| --- | --- | --- |
| `main` | Production. What is deployed. | `develop` (releases), `hotfix/*` |
| `develop` | Integration. Default target for all PRs. | `feat/*`, `fix/*`, `chore/*`, `docs/*`, `refactor/*`, `test/*` |
| `feat/*` and friends | Short-lived, one concern each. | branched from `develop` |
| `hotfix/*` | Urgent production fix. | branched from `main` |

`main` and `develop` are protected. You cannot push to them directly, and you
cannot force-push. Everything lands through a pull request.

A `hotfix/*` branch merges into `main` **and** back into `develop`, so the fix
does not get lost on the next release.

## Naming a branch

```
<type>/<short-kebab-description>
```

Types are the same set used for PR titles: `feat`, `fix`, `chore`, `docs`,
`refactor`, `test`.

```
feat/reading-upload
feat/instructor-analytics
fix/session-retry-count
chore/dockerize-backend
docs/api-setup-guide
```

Keep it short and descriptive. No issue numbers for now — we are not tracking
work in GitHub Issues. If that changes, `feat/12-reading-upload` slots in
without breaking anything.

`/start-branch` will create one of these for you off an up-to-date `develop`.

## Starting work

```bash
git checkout develop
git pull
git checkout -b feat/reading-upload
```

## Commit messages

Commits inside a branch are working notes. They are squashed when the PR merges,
so they do not survive into `develop` and do not need prefixes.

Three rules:

- **Imperative mood** — "add retry handling", not "added" or "adds"
- **Subject under ~72 characters**
- **Body only when the *why* is not obvious** from the diff

```
add retry handling to the submit endpoint
fix off-by-one in the attempt counter
wire the analytics query to the class view
```

The `feat:` / `fix:` classification lives on the **PR title**, which is what
actually becomes the commit message on `develop`. See
[pull-requests.md](pull-requests.md).

### One exception

Work merged with history preserved rather than squashed — currently only the
`develop → main` release merge — keeps its individual commits. Those should
follow the Conventional Commits format, since they end up in `main`'s history.

## Merging

| Merge | Strategy | Why |
| --- | --- | --- |
| `feature → develop` | **Squash** | One clean commit per PR. Messy WIP inside a branch does not matter. |
| `develop → main` | **Regular merge** | Preserves one commit per feature on `main`. Squashing a release would flatten every feature in it into a single commit. |

Delete the branch after it merges.

## Keeping a branch current

Prefer rebasing onto `develop` while a branch is still yours alone:

```bash
git fetch origin
git rebase origin/develop
```

If the branch is already pushed and someone else has pulled it, merge instead of
rebasing so you do not rewrite history they already have.
