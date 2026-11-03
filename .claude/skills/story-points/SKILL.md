---
name: story-points
description: Estimates the story points (1, 2, 3, 5, 8, 13, 21) of a user story .md from the code repository's commit history, then has the user confirm the value. Use whenever a story is being written or saved to stories/, when a story to upload has no points, or when the user asks to estimate, score, rate or review the points of stories.
---

# Story points estimator

Suggests points on the Fibonacci scale **1, 2, 3, 5, 8, 13, 21** by looking at the commits
that implemented the story. The script gives a first number. You review the evidence,
adjust it if needed, explain it in one line, and **the user confirms**. Only then write the
value to the story's `**Points:**` field (`**Pontos:**` in Portuguese).

## Setup

`CODE_REPO_PATH` in `.env` points to the code repository the stories describe, e.g.
`CODE_REPO_PATH=C:/projects/my-app`. If it is missing, ask the user for the path and add it.
`--repo <path>` overrides it for one run.

## Steps

1. **Run the estimator** for the stories being written or uploaded:

   ```bash
   python -X utf8 .claude/skills/story-points/scripts/estimate_points.py <story.md ...> --since <date>
   ```

   Use `--since` about a month before the story's `**Date:**` to keep the search focused.
   `--json` gives the same data in machine-readable form.

2. **Check the commits it picked.** For each story, the script lists the matched commits:
   - no tag: the commit subject matches the story title. This is the strongest signal;
   - `[shared]`: the commit also matched another story, so only the files this story names
     (and their tests) are counted;
   - `[partial: only named files]`: no subject matched, so the script fell back to commits
     that touch files named in the story, counting only those files.

   Drop unrelated commits and add missing ones by rerunning with
   `--commits sha1,sha2`. Look at `git -C <repo> show --stat <sha>` when in doubt.

3. **Judge the number.** The script's rule: code lines changed (ignoring lockfiles,
   changelogs, version files, builds and images) give a base value, and each of these adds
   one step: 3 or more code areas (backend, frontend, migrations, infra), and risk (auth,
   login, permissions, roles, tokens, security, migrations). Then adjust with what the
   numbers cannot see:

   | Points | Typical story |
   |---|---|
   | 1 | One-line or CSS fix, config value, copy change |
   | 2 | Small fix in one place, with no new behaviour |
   | 3 | Small feature or fix in a couple of files, simple rules |
   | 5 | A feature across backend and frontend, or a fix with tricky rules |
   | 8 | Several screens or services, new tables, more than a few rules |
   | 13 | Large feature, cross-cutting change, migrations of existing data |
   | 21 | Very large or uncertain: new module, many areas, high risk |

   - Generated, copied or vendored code inflates lines: lower the value.
   - Delicate logic in few lines (permissions, money, data migration): raise it.
   - Without matching commits (work not committed yet), estimate from the story's tasks
     and acceptance criteria using the table, and say that there was no commit evidence.

4. **Ask the user to confirm**, all stories in one message, as a list:
   `<title>: <points> (<one-line reason>, commits <sha>, <sha>)`. Say they can reply only
   with the ones they want to change. Write the confirmed values to `**Points:**`
   (`**Pontos:**`), right after `**Date:**` / `**Período:**`.

Never upload a story with an estimate that the user has not confirmed.
