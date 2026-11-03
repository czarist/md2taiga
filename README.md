<h1 align="center">md2taiga</h1>

<h3 align="center">One Markdown file per story. One command to Taiga.</h3>

<p align="center">
  <b>Write user stories as Markdown and push them to Taiga, with all their tasks, into a sprint or the backlog.</b><br>
  A dependency-free Python script validates the files and calls the Taiga API. A Claude Code skill writes the stories for you.
</p>

<p align="center">
  <a href="https://www.python.org"><img alt="Python 3.8+" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="https://taiga.io"><img alt="Target: Taiga" src="https://img.shields.io/badge/target-Taiga-4DC8A8?style=flat-square&logo=task&logoColor=white"></a>
  <a href=".claude/skills/taiga-stories/story-template.md"><img alt="Format: Markdown" src="https://img.shields.io/badge/format-Markdown-000000?style=flat-square&logo=markdown&logoColor=white"></a>
  <a href=".claude/skills/taiga-stories/SKILL.md"><img alt="Agent: Claude Code skill" src="https://img.shields.io/badge/agent-Claude%20Code-D97757?style=flat-square&logo=claude&logoColor=white"></a>
  <img alt="Dependencies: none" src="https://img.shields.io/badge/deps-none-6BA539?style=flat-square">
  <img alt="CLI: validate and upload, version 0.1.0" src="https://img.shields.io/badge/CLI-validate%20%C2%B7%20upload%20%C2%B7%200.1.0-111111?style=flat-square">
</p>

<br>

<p align="center">
  <a href="#what-it-does">What it does</a> ·
  <a href="#how-a-story-maps">Mapping</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#commands">Commands</a> ·
  <a href="#story-format">Story format</a> ·
  <a href="#with-claude-code">Claude Code</a> ·
  <a href="#layout">Layout</a> ·
  <a href="#troubleshooting">Troubleshooting</a>
</p>

<br>

## What it does

Each story lives in its own `.md` file under `stories/`. md2taiga reads those files and creates, in any Taiga project, one user story per file and one task per item under `## Tasks`. You choose the destination on every upload: a sprint or the backlog.

This project is not affiliated with Taiga or Kaleidos.

- **Reviewable.** The title, description, acceptance criteria and tasks all live in one file, so they can go through a pull request.
- **Safe to re-run.** A story whose title already exists in the project is skipped. An interrupted upload resumes the same story instead of creating a duplicate.
- **WAF-tolerant.** Some Taiga instances sit behind a proxy (for example Cloudflare) that blocks text that looks like SQL or HTML. A blocked description is retried in plainer forms, and every rewrite is reported at the end.
- **Validated offline.** `validate` catches missing sections, a broken user story sentence and gaps in task numbering, without a token or network access.
- **Bilingual.** Headings can be in English (`# Story:`, `## Tasks`) or in Portuguese (`# História:`, `## Tarefas`).
- **No dependencies.** Python standard library only.

## How a story maps

```text
stories/automatic-slug.md  ──►  Taiga user story #575  (21 pts · assigned to you · Sprint 34)
  ## Tasks                         ├─ task #576  Slug composable
    1. **Slug composable**         ├─ task #577  Apply to the forms
    2. **Apply to the forms**      └─ task #578  Update changelog and version
    3. **Update changelog...**
```

| Markdown | Taiga |
|---|---|
| Text after `# Story:` | User story title |
| Whole file minus the first line | User story description |
| `N. **Title**` under `## Tasks` | Task title |
| Indented lines below a task | Task description |

- **Assignee.** The token owner, on the story and on every task.
- **Points.** The story's `**Points:**` header field, else `TAIGA_POINTS`, on the project's computable role. With Claude Code, the agent asks the points of each story before uploading.
- **Status.** The project defaults.

## Quick start

```sh
git clone https://github.com/czarist/md2taiga.git
cd md2taiga
cp .env.example .env
```

Set the project link in `.env`:

```ini
TAIGA_PROJECT_URL=https://taiga.example.com/project/my-project
TAIGA_POINTS=21
STORIES_DIR=stories
```

`.env` holds no secrets and is ignored by git. The token is never read from it.

Write a story in `stories/` from the [template](.claude/skills/taiga-stories/story-template.md), then validate, preview and upload it:

```sh
S=.claude/skills/taiga-stories/scripts/taiga_stories.py

python -X utf8 $S validate
python -X utf8 $S upload --sprint "Sprint 34" --dry-run
TAIGA_TOKEN='<token>' python -X utf8 $S upload --sprint "Sprint 34"
```

**Token.** Open Taiga in the browser, press F12, go to the Console, run `localStorage.getItem("token")` and copy the result without the quotes. Pass it inline for each session. Do not put it in `.env` or commit it.

## Commands

| Command | What it does |
|---|---|
| `validate [file.md ...]` | Checks the format. No network, no token. Exits non-zero on errors. Warnings do not fail. |
| `upload --sprint "<name>"` | Creates the stories and tasks in that sprint. The name must match Taiga exactly. |
| `upload --backlog` | Creates them in the backlog. |
| `--dry-run` | Lists what would be created, without calling the API. |
| `--force` | Creates a story even when the title already exists in the project. |
| `--points <value>` | Default points for stories without a `**Points:**` field, overriding `TAIGA_POINTS`. |
| `--project-url <url>` | Overrides `TAIGA_PROJECT_URL` for this run. |
| `--dir <path>` | Reads stories from another folder. |

File names at the end limit a run to those stories: `upload --backlog automatic-slug.md`.

## Story format

```markdown
# Story: Automatic slug from the title

**Project:** MyApp
**Branch:** `feature/slug`
**Version:** 4.0.9.5
**Date:** 19/10/2026
**Points:** 8

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

Tasks are grouped under `### Backend`, `### Frontend`, `### Tests` and `### Documentation`, and numbering is continuous across the groups. The full rules and the Portuguese heading table are in [SKILL.md](.claude/skills/taiga-stories/SKILL.md).

## With Claude Code

The repository ships the skill [`.claude/skills/taiga-stories`](.claude/skills/taiga-stories/SKILL.md), and [`AGENTS.md`](AGENTS.md) holds the same rules for any coding agent. Open the folder in Claude Code and ask:

> Write a story for the new PDF page feature.
>
> Upload the new stories to Taiga.

The agent writes the story in the standard format and in the language of the request, then validates it. Before each upload, it asks in the chat for the destination (a sprint or the backlog) for the session token and for the points of each story.

## Layout

```text
.
├── AGENTS.md                         rules for coding agents
├── .env.example                      configuration template
├── stories/                          your stories (*.md is git-ignored)
└── .claude/skills/taiga-stories/
    ├── SKILL.md                      writing rules, upload steps, lessons learned
    ├── story-template.md
    └── scripts/taiga_stories.py      validate · upload
```

Story files are git-ignored by default, because they often describe internal systems. Remove `stories/*.md` from `.gitignore` to version them.

## Troubleshooting

| Symptom | Meaning |
|---|---|
| `403` with an HTML page ("Just a moment...") | The proxy's WAF blocked the text. The script retries with plainer text and lists what it changed. |
| `403` with `PermissionDenied` | A Taiga permission error. Some roles cannot delete user stories, so check `--dry-run` before uploading. |
| `Sprint "..." not found` | The name must match the sprint in Taiga exactly. |
| `exists in project (#N), skipped` | A story with that title already exists. `--force` creates it anyway. |
| Garbled accents on Windows | Run Python with `-X utf8`. |
