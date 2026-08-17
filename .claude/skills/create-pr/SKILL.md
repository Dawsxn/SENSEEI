---
name: create-pr
description: Open a pull request from the current branch following the repo's conventions — a Conventional Commits PR title and a filled-in description template, targeting develop. Use when the user asks to open, create, make, raise, or submit a PR or pull request, or says their branch is done and ready for review.
---

# Create a pull request

Drafts the title and description from the actual diff, shows them to the user,
and opens the PR only after they confirm.

Conventions live in `docs/conventions/pull-requests.md`. This skill applies
them; that file is the source of truth.

## Steps

1. **Guard.**

   ```bash
   git rev-parse --abbrev-ref HEAD
   git status --porcelain
   ```

   - If on `main` or `develop`, stop. PRs come from feature branches.
   - If there are uncommitted changes, tell the user and ask whether to commit
     them first. Do not commit on your own.
   - If `gh` is not authenticated (`gh auth status`), say so and stop.

2. **Push the branch if it has no upstream.**

   ```bash
   git push -u origin HEAD
   ```

3. **Read what actually changed.** Do not guess from the branch name.

   ```bash
   git fetch origin
   git diff origin/develop...HEAD --stat
   git log origin/develop..HEAD --format='%s%n%b'
   ```

   For anything non-trivial, read the diff itself, not just the stat.

4. **Draft the title.**

   ```
   <type>(<scope>): <subject>
   ```

   - **Type** from the branch prefix, unless the diff clearly says otherwise. If
     the branch says `feat/` but every change is a bug fix, use `fix` and tell
     the user why.
   - **Scope** from which paths changed: `api`, `session`, `analytics`,
     `orchestrator`, `agent`, `ui`, `db`, `eval`. Omit the scope if the change
     spans several areas rather than inventing a broad one.
   - **Subject** imperative, lowercase, no trailing period, under ~72 characters
     including the prefix.

5. **Draft the description** using `.github/pull_request_template.md`.

   Required, and CI fails without them:

   - **Summary** — one to three sentences on what and why. Written for someone
     who has not followed the branch.
   - **Changes** — one bullet per meaningful piece. Group related files rather
     than listing every path.
   - **How to test** — concrete steps a reviewer can follow. Real commands and
     real URLs where they apply.

   Optional, delete the heading entirely when unused:

   - **Screenshots** — only if the diff touches UI files. Do not fabricate
     these: leave the section with a note asking the user to attach them.
   - **Notes & caveats** — follow-ups, known limitations, anything risky.

6. **Show the user the full title and description and ask for confirmation.**
   Do not skip this. Opening a PR is visible to the whole team.

7. **Open it.**

   ```bash
   gh pr create --base develop --title "<title>" --body "<body>"
   ```

   Use `--base main` only for a `hotfix/*` branch.

8. **Report the PR URL.**

## Rules

- Never merge the PR. Opening and merging are separate decisions, and merging is
  the user's.
- Never force-push to make the diff tidier.
- If the branch is behind `develop`, mention it so the user can rebase, but do
  not rebase for them without asking.
- If the diff is empty against `develop`, say so instead of opening an empty PR.
