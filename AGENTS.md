# AGENTS.md

**md2taiga**: general-purpose tooling to write user stories as Markdown and upload them, with their
tasks, to any Taiga project. There is no application code here.

## Layout

- `stories/`: one story per `.md` file. These files are ignored by git.
- `.env`: Taiga project link, ignored by git. Copy it from `.env.example`.
- `.claude/skills/taiga-stories/`: the skill.
  - `SKILL.md`: writing rules, upload procedure and lessons learned.
  - `story-template.md`: template for new stories.
  - `scripts/taiga_stories.py`: `validate` and `upload` commands (Python standard library only).

## Writing stories

- Follow `story-template.md` and the rules in `SKILL.md`.
- **Write the story in the language of the request.** If the user asked in Portuguese, the
  whole story is in Portuguese, headings included (`# História:`, `## Tarefas`...). If they
  asked in English, it is in English. See the heading table in `SKILL.md`.
- File names: lowercase, no accents, words with hyphens, inside `stories/`.
- **Ask the points of each story before saving it to `stories/`.** There is no default.
  Write the answer in the `**Points:**` header field (`**Pontos:**` in Portuguese stories).
  The value must exist in the project's point scale (e.g. 1, 2, 3, 5, 8, 13, 21).
- Before handing a story over, run:

  ```bash
  python -X utf8 .claude/skills/taiga-stories/scripts/taiga_stories.py validate
  ```

## Uploading to Taiga

Follow "Uploading to Taiga" in `SKILL.md`. Key rules:

- **Every upload**, ask the user in the chat for the destination (sprint name or backlog)
  and the session token. Do not reuse answers from earlier uploads.
- **If a story to upload has no points**, ask the user for them before uploading and
  save them in its `**Points:**` field. The upload refuses stories without points.
- **Never** write the token to `.env` or to any file in the repository. Pass it as an
  inline `TAIGA_TOKEN` environment variable.
- Always run `--dry-run` first.
- Avoid duplicates. Members may not be allowed to delete user stories in Taiga.
