# md2taiga

Write user stories as Markdown, then push them to [Taiga](https://taiga.io), with all their tasks, in one command.

md2taiga is a small Python script plus a [Claude Code](https://claude.com/claude-code) skill. You (or your coding agent) keep each story in a `.md` file with a fixed structure. md2taiga validates the files and creates the user stories and their tasks in any Taiga project, either in a sprint or in the backlog.

```text
stories/automatic-slug.md  ──►  Taiga user story #575  (21 pts, assigned to you, Sprint 34)
  ## Tasks                         ├─ task #576  Slug composable
    1. **Slug composable**         ├─ task #577  Apply to the forms
    2. **Apply to the forms**      └─ task #578  Update changelog and version
    3. **Update changelog...**
```

## Features

- **One file per story.** The title, description, acceptance criteria and tasks all live in one Markdown file you can review in a pull request.
- **Sprint or backlog.** You choose the destination on every upload.
- **Safe to re-run.** Stories whose title already exists in the project are skipped, and an interrupted upload resumes the same story instead of creating a duplicate.
- **Works with WAF-protected Taiga instances.** If a reverse proxy (for example Cloudflare) blocks a description that looks like SQL or HTML, the text is retried in plainer forms, and every rewrite is reported.
- **Format validation.** It runs offline and catches missing sections, a broken user story sentence or gaps in task numbering.
- **English or Portuguese.** Both heading sets are parsed.
- **No dependencies.** Python 3.8+ standard library only.

## Quick start

```bash
git clone https://github.com/<you>/md2taiga.git
cd md2taiga
cp .env.example .env        # set TAIGA_PROJECT_URL to your project link
```

`.env`:

```ini
TAIGA_PROJECT_URL=https://taiga.example.com/project/my-project
TAIGA_POINTS=21          # point value per story; empty = no points
STORIES_DIR=stories
```

Write a story in `stories/` from the [template](.claude/skills/taiga-stories/story-template.md), then:

```bash
S=.claude/skills/taiga-stories/scripts/taiga_stories.py

python -X utf8 $S validate                                   # check the format (offline)
python -X utf8 $S upload --sprint "Sprint 34" --dry-run      # preview
TAIGA_TOKEN='<token>' python -X utf8 $S upload --sprint "Sprint 34"
TAIGA_TOKEN='<token>' python -X utf8 $S upload --backlog     # or straight to the backlog
```

Pass file names at the end to upload only some stories, for example `upload --backlog my-story.md`.

### Getting the token

Open Taiga in your browser, press **F12**, go to **Console**, run the line below and copy the result without the quotes:

```js
localStorage.getItem("token")
```

The token is only read from the `TAIGA_TOKEN` environment variable. Do not put it in `.env` or commit it.

## Using it with Claude Code

The repository ships the skill `.claude/skills/taiga-stories`, and [`AGENTS.md`](AGENTS.md) holds the rules for any coding agent. Open the folder in Claude Code and ask, for example:

> Write a story for the new PDF page feature.
>
> Upload the new stories to Taiga.

The agent writes the story in the standard format and in the language of your request, then validates it. Before each upload it asks for the destination (a sprint name or the backlog) and for your session token.

## Story format

```markdown
# Story: Automatic slug from the title

**Project:** MyApp
**Branch:** `feature/slug`
**Version:** 4.0.9.5
**Date:** 19/10/2026

## User story

**As** a content author,
**I want** the slug filled in while I type the title,
**so that** I don't have to write the page address by hand.

## Description

Plain prose for the product owner.

## Acceptance criteria

- [x] The slug follows the title on page creation.
- [ ] Editing the slug by hand stops the automatic fill.

## Tasks

### Frontend

1. **Slug composable**
   `useAutomaticSlug.js` with `makeSlug` and manual-edit tracking.

### Documentation

2. **Update changelog and version**
   Changelog entry for version 4.0.9.5.

## Deployment notes

- Front-end build only.
```

| Markdown | Taiga |
|---|---|
| Text after `# Story:` | User story title |
| Whole file without the first line | User story description |
| `N. **Title**` under `## Tasks` | Task title |
| Indented lines below a task | Task description |

Stories are assigned to the token owner, get `TAIGA_POINTS` on the project's computable role and start in the project's default statuses. Tasks are assigned to the token owner too.

The full writing rules, including the Portuguese headings, are in [SKILL.md](.claude/skills/taiga-stories/SKILL.md).

## Layout

```text
.
├── AGENTS.md                         rules for coding agents
├── .env.example                      configuration template
├── stories/                          your stories (*.md are git-ignored)
└── .claude/skills/taiga-stories/
    ├── SKILL.md                      writing rules, upload steps, lessons learned
    ├── story-template.md
    └── scripts/taiga_stories.py      validate / upload
```

Story files are git-ignored by default, because they often describe internal systems. Remove `stories/*.md` from `.gitignore` if you want to version them.

## Troubleshooting

| Symptom | Meaning |
|---|---|
| `403` with an HTML page ("Just a moment...") | The proxy's WAF blocked the text. The script retries with plainer text and lists what it changed. |
| `403` with `PermissionDenied` | A real Taiga permission error. Some roles cannot delete user stories, so check the `--dry-run` output before uploading. |
| `Sprint "..." not found` | Use the exact sprint name as shown in Taiga. |
| `exists in project (#N), skipped` | A story with the same title already exists. Use `--force` to create it anyway. |
| Garbled accents on Windows | Run Python with `-X utf8`. |
