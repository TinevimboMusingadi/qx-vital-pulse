---
name: my-commit-style
description: Defines Tinevimbo's git commit workflow — read each changed file and review its diff first, then create one commit per file instead of one big commit per feature, producing a clean, easy-to-review, easy-to-bisect git history. Use this skill any time you're asked to commit code (commit this, save these changes, commit my changes), stage and commit, wrap up a coding session with a commit, or clean up a working tree before a PR — even if the user just says commit with no further detail. Check this skill before running git commit so commits never get bundled by feature.
compatibility: Requires shell access to run git commands (status, diff, add, commit, log).
---

# My Commit Style

When it's time to commit, don't sweep every changed file into one "added feature X" commit. Make one commit per file. Each commit should tell a reviewer exactly what changed in exactly one file, and why, nothing more and nothing less. This keeps `git log` readable, makes `git bisect` actually useful, and lets any single file's change be reverted without dragging the rest along with it.

## Workflow

### 1. Get the real list of changed files — don't rely on memory

Run:
```bash
git status --porcelain
```

Work from this output, not from recollection of what you edited — it's easy to forget a file touched two steps ago. The status codes that matter:

- `M` — modified
- `A` — added / already staged
- `??` — untracked / new file
- `D` — deleted
- `R` — renamed

Every changed code file in that list gets its own commit. If the list is empty, tell the user there's nothing to commit rather than inventing one.

### 2. For each file, in turn: read it, review its diff, commit it alone

Work through the list one file at a time:

1. **Read the whole file**, not just the diff, so the change is understood in context — a one-line diff reads differently once you know it sits inside a retry loop versus a config default.
2. **Review that file's diff in isolation**: `git diff -- <file>` (or `git diff --cached -- <file>` if it's already staged). This is what the commit message will describe.
3. **Stage only this file**: `git add <file>`.
4. **Commit it immediately**, before touching the next file (see message format below).
5. Move to the next file and repeat.

Stage and commit one file at a time rather than staging several and committing once — that's the whole difference between this workflow and a feature-level commit. If the changes have a natural dependency order (a new helper function and the file that calls it, say), commit the dependency first so every intermediate commit still makes sense on its own.

### 3. The one real exception: changes that can't survive being split

Occasionally a change is genuinely atomic across files — renaming a function and updating its call sites, or bumping a version in `package.json` alongside its `package-lock.json`. Splitting these would leave an intermediate commit that doesn't build or doesn't make sense by itself. In that specific case, commit the smallest set of files that has to move together, and say so in the message, e.g. `refactor(auth): rename validateUser to verifyUser (+ call sites)`. Treat this as the exception, not the default — most changes really do stand alone file by file.

This skill splits commits at the file level, not the hunk level — it won't break a single file's change into multiple commits.

### 4. Show the result

Once every file is committed, run:

```bash
git log --oneline -n <number of files just committed>
```

and show it to the user. That's the actual payoff: instead of one opaque "update dashboard" commit, they get a short, readable list where every line maps to exactly one file and one clear change.

## Commit message format

`<type>(<scope>): <what changed, and why if it isn't obvious>`, where `<scope>` is the file or module name (extension optional).

Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`, `perf`.

**Example 1:**
Input: added a retry wrapper around the API client because requests were timing out intermittently
Output: `fix(api_client): add retry wrapper to handle transient timeouts`

**Example 2:**
Input: created a new file with email and phone validation helpers
Output: `feat(validators): add email and phone validation helpers`

**Example 3:**
Input: removed the old CSV export function, superseded by last week's JSON exporter
Output: `chore(export): remove unused CSV export, superseded by JSON export`

Keep the subject line under about 72 characters. A per-file commit's scope is already small, so most won't need more than the one-liner — add a short body after a blank line only when a file's change genuinely needs more explanation than that.
