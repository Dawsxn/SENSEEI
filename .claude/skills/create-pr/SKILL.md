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

   - **Summary**: what the PR does. See the rules below, they matter.
   - **Changes**: one bullet per meaningful piece. Group related files rather
     than listing every path.

   Optional, delete the heading entirely when unused:

   - **How to test**: concrete steps a reviewer can follow, with real commands
     and real URLs. Include it when there is something to run or click. Omit it
     for documentation, config, and anything with nothing to execute. Do not
     invent a procedure just to fill the section.
   - **Screenshots**: only if the diff touches UI files. Do not fabricate
     these: leave the section with a note asking the user to attach them.
   - **Notes & caveats**: one line each, three or four at most. A caveat earns
     its place only if it changes what a reviewer does or watches for. No
     hedging, no restating **Changes**, no recounting what you considered and
     rejected. Delete the section rather than padding it.

   **Writing the summary.** Lead with what the PR does. First sentence, present
   tense, starting with the change:

   ```
   Adds retry handling to the submit endpoint.
   Moves the Assessment Agent into a shared package.
   ```

   Do not open with background, with the state of the world before the change,
   or with what the PR is "part of". Add a second sentence of why only when the
   reason is not obvious from the change. Two sentences is usually the whole
   summary; if it runs longer, the detail belongs in **Changes**.

   **Never reference the thesis manuscript.** No chapters, sections, tables, or
   figures. The manuscript is not in the repository and a reviewer cannot follow
   the pointer. State the decision or behaviour directly instead of citing where
   it came from. This applies to the PR title and description only; repository
   documentation may cite it.

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
