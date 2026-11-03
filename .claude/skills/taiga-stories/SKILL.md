---
name: taiga-stories
description: Writes user stories as Markdown files in the standard format and uploads them to Taiga, each with the tasks listed under "## Tasks". Use when the user asks to write, create, standardize or review a story .md, or to upload, register or push stories and tasks to Taiga, a sprint or the backlog.
---

# Taiga stories

There is no browser control. Uploads go through the Taiga REST API with
`scripts/taiga_stories.py`, which uses only the Python standard library. The same
tooling works for any Taiga project, which is configured in `.env`.

## Setup (once per repository)

1. Copy `.env.example` to `.env` at the repository root and set `TAIGA_PROJECT_URL`
   to the project link, e.g. `https://taiga.example.com/project/my-project`.
2. Optionally set `STORIES_DIR` (default `stories`).

`.env` holds no secrets and is ignored by git. The token **never** goes in it.

## Writing stories

Each story is one `.md` file in `stories/`, following [story-template.md](story-template.md).

- **File name:** lowercase, no accents, words with hyphens (`automatic-slug.md`).
- **First line:** `# Story: <title>`. The text after "Story:" becomes the Taiga title.
  For bug fixes, use `Fix — <what was happening>`.
- **Header:** `**Project:**`, `**Branch:**`, `**Version:**`, `**Date:**` and `**Points:**`,
  one per line.
- **Points:** there is no default. **Before saving a new story to `stories/`, ask the user
  its points** and write them in `**Points:**` (`**Pontos:**` in Portuguese). The value must
  be a name in the project's point scale (e.g. 1, 2, 3, 5, 8, 13, 21). When writing several
  stories, ask for all of them in one message, listing them by title.
- **Sections, in this order:** `## User story` (**As** / **I want** / **so that**, each bold
  on its own line), `## Description` (prose for the product owner, no code jargon),
  `## Acceptance criteria` (`- [ ]` checklist, `[x]` for what is done and tested),
  `## Tasks` and `## Deployment notes` (or `## Notes` when it is not about deployment).
- **Tasks:** group them under `### Backend`, `### Frontend`, `### Tests` and
  `### Documentation`, in that order, leaving out empty groups. Each task is
  `N. **Title**` with its description indented on the next line. Numbering is continuous
  across groups.
- **Language:** write the whole story, headings included, in the language of the user's
  request. A request in Portuguese gets a story in Portuguese. Both heading sets are parsed:

  | English | Portuguese |
  |---|---|
  | `# Story:` | `# História:` |
  | `**Project:**` / `**Branch:**` / `**Version:**` / `**Date:**` / `**Points:**` | `**Projeto:**` / `**Branch:**` / `**Versão:**` / `**Período:**` / `**Pontos:**` |
  | `## User story` (**As** / **I want** / **so that**) | `## História de usuário` (**Como** / **quero** / **para**) |
  | `## Description` | `## Descrição` |
  | `## Acceptance criteria` | `## Critérios de aceite` |
  | `## Tasks` (`### Backend`, `### Frontend`, `### Tests`, `### Documentation`) | `## Tarefas` (`### Backend`, `### Frontend`, `### Testes`, `### Documentação`) |
  | `## Deployment notes` / `## Notes` | `## Observações para implantação` / `## Observações` |
  | `Fix — ...` | `Correção — ...` |
- **Firewall-friendly text:** in descriptions, avoid a `;` right before `code` (use a full
  stop), literal tags like `<script>` (write "the script tag"), and chains of
  `Class::method` next to routes. The script works around these, but the text gets worse.

Check the format (no network, no token):

```bash
python -X utf8 .claude/skills/taiga-stories/scripts/taiga_stories.py validate [file.md ...]
```

Fix errors. A task without description is an acceptable warning. A missing `**Points:**`
is only a warning here, but it blocks the upload.

## Uploading to Taiga

### Always ask first, in the chat, every time

Use AskUserQuestion, or a plain question if it is unavailable. Do not reuse earlier answers:

1. **Destination:** which sprint (exact name, e.g. `Sprint 34`) or **backlog**.
2. **Session token:** in the open Taiga tab, F12 > Console >
   `localStorage.getItem("token")`. Use it only as an inline environment variable for
   the command. Never write it to `.env` or to any file.
3. **Missing points:** if any story to upload has no `**Points:**` (the `--dry-run` shows
   `MISSING`), ask the points of those stories, listing them by title. Write each answer
   to the story's `**Points:**` line (`**Pontos:**` in Portuguese), right after
   `**Date:**` / `**Período:**`. Stories that already have points are not asked again.
   The upload stops before creating anything while any story lacks a valid value.

If `.env` is missing, also ask for the Taiga project link and create `.env` from
`.env.example`.

### Steps

```bash
S=.claude/skills/taiga-stories/scripts/taiga_stories.py
python -X utf8 $S validate
python -X utf8 $S upload --sprint "Sprint 34" --dry-run        # or --backlog
TAIGA_TOKEN='<token>' python -X utf8 $S upload --sprint "Sprint 34"
```

Pass file names at the end to upload only some stories. Then report to the user how many
stories and tasks were created, plus any texts the script rewrote (and any task whose
description was dropped).

Defaults: the token owner is the assignee of stories and tasks, statuses are the project
defaults, and points come from each story's `**Points:**` field, on the project's
computable role.

The script:
- skips stories whose **title already exists in the project**. Use `--force` only if the
  user asks;
- resumes an interrupted run without duplicating (state in `stories/.taiga_state.json`).
  If it stops, **just run it again**;
- rewrites texts blocked by the firewall and lists them at the end.

Do not chain other creating commands with `;` after a step that can fail. A failure
halfway through can create duplicates.

## Lessons learned

- **Cloudflare 403 with an HTML body** ("Just a moment...") means the WAF blocked the text,
  not a permission problem. The script retries with plainer variants. If a task ends up
  with no description, rewrite it as plain prose (no backticks, no `::`) and PATCH it,
  sending the current `version`.
- **403 with JSON `PermissionDenied`** is a real permission error. Regular members may be
  unable to **delete user stories** (tasks are fine), so avoid duplicates. If one happens,
  reuse the story with PATCH (subject, description, points, milestone, assigned_to,
  `version`) instead of deleting it.
- Points go in `points: {"<computable role id>": <point id>}`, and the point id is looked
  up by its name in the project scale.
- On Windows, Python does not see Git Bash's `/tmp`. Use Windows paths, and run Python with
  `-X utf8` so accents print correctly.
