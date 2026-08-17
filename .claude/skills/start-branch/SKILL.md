---
name: start-branch
description: Create a correctly named git branch off an up-to-date develop, following the repo's branch naming convention. Use when the user wants to start new work, start a feature, begin a fix, create a branch, or asks what branch they should be on before making changes.
---

# Start a branch

Creates a branch that already conforms to `docs/conventions/git-workflow.md`, so
naming is correct by construction rather than by memory.

## Steps

1. **Check the working tree is clean.**

   ```bash
   git status --porcelain
   ```

   If there are uncommitted changes, stop and ask the user what to do with them.
   Do not stash or discard anything on your own.

2. **Work out the type and description.**

   If the user did not say, infer the type from what they describe and confirm
   it with them before continuing.

   | Type | Use for |
   | --- | --- |
   | `feat` | A new capability |
   | `fix` | A bug fix |
   | `refactor` | Restructuring with no behaviour change |
   | `chore` | Tooling, config, dependencies |
   | `docs` | Documentation only |
   | `test` | Tests only |

   The description is short kebab-case, two to four words. `reading-upload`,
   `session-retry-count`, `dockerize-backend`. Not a sentence.

3. **Pick the base branch.**

   `develop` for everything, except `hotfix/*` which branches from `main`. If
   the user is asking for an urgent production fix, use `hotfix/` and `main`.

4. **Create it.**

   ```bash
   git checkout <base>
   git pull
   git checkout -b <type>/<description>
   ```

5. **Report** the new branch name and what it was based on.

## Rules

- Never create a branch directly off another feature branch unless the user
  explicitly asks for it. Branching off `develop` keeps history flat.
- If a branch with that name already exists, say so and suggest a different
  description rather than switching to it silently.
- Do not push the branch. It gets pushed when there is something on it.
