# Changelog

All notable changes to md2taiga are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `CHANGELOG.md` and `ROADMAP.md`.

## [0.3.0] - 2026-11-03

### Added
- `story-points` skill, which estimates story points (1, 2, 3, 5, 8, 13, 21) from the git history of the code repository.
- `estimate_points.py`, which matches commits to a story:
  - first by commit subjects that share words with the story title;
  - then by files named in the story that few commits touch;
  - and, as a last resort, by any named file, counting only those files.
- In commits shared by several stories, only the files that the story names, and their tests, are counted.
- How a suggestion is computed:
  - a base value comes from the code lines changed, ignoring lockfiles, changelogs, version files, builds and images;
  - one step is added for 3 or more code areas (backend, frontend, migrations, infra);
  - one more step is added for risky paths (auth, login, permissions, roles, tokens, security, migrations).
- `--commits` to pick the commits by hand, `--since` to narrow the search, and `--json` for machine-readable output.
- `CODE_REPO_PATH` in `.env.example`.

### Changed
- `AGENTS.md`, the `taiga-stories` skill and the README now tell the agent to estimate points with `story-points` before saving a story and before uploading one without points. The user always confirms the value.

## [0.2.0] - 2026-11-03

### Added
- Optional `**Points:**` header field (`**Pontos:**` in Portuguese) on each story.
- `validate` warns when a story has no points. `upload --dry-run` shows `MISSING` for those stories.
- The README now has a centered header, badges and a navigation bar.

### Changed
- **Breaking:** points come only from each story's `**Points:**` field. Before creating anything, `upload` checks every story and stops if one has no points or a value that is not in the project's point scale.
- The agent asks for the points of each story before saving it, and again before uploading if any are missing.

### Removed
- **Breaking:** the `TAIGA_POINTS` setting and the `--points` flag. There is no default point value any more.

## [0.1.0] - 2026-11-03

First public version, generalized from a one-off script that uploaded 27 stories and 179 tasks to a Taiga sprint.

### Added
- `taiga_stories.py` with two commands:
  - `validate`: checks the story format offline (sections, header fields, the user story sentence, task numbering, file names);
  - `upload --sprint "<name>" | --backlog`: creates one Taiga user story per `.md` file and one task per `N. **Title**` item under `## Tasks`.
- Configuration in `.env`: `TAIGA_PROJECT_URL` (any Taiga project) and `STORIES_DIR`. The token is only read from `TAIGA_TOKEN`, per session.
- The token owner is the assignee of every story and task, and statuses are the project defaults.
- Duplicate protection:
  - stories whose title already exists in the project are skipped, and `--force` creates them anyway;
  - an interrupted run resumes the same story instead of creating a second one (`stories/.taiga_state.json`).
- Firewall fallback. When a WAF in front of Taiga (for example Cloudflare) returns a 403 HTML page for text that looks like SQL or HTML, the description is retried in plainer forms: `;` becomes `.`, then backticks and `<tags>` are removed, then `::` is removed, and finally the description is dropped. Every rewrite is reported. A JSON `PermissionDenied` is treated as a real permission error.
- `--dry-run`, `--project-url` and `--dir` options, plus file names as arguments.
- English and Portuguese headings (`# Story:` / `# História:`, `## Tasks` / `## Tarefas`...).
- `taiga-stories` Claude Code skill, with writing rules, the upload procedure and lessons learned.
  - Before every upload, the agent asks for the destination (a sprint or the backlog) and for the session token.
  - Stories are written in the language of the request.
- `story-template.md`, `AGENTS.md`, `README.md` and `.env.example`.
- `.gitignore` covers `.env`, `stories/*.md` and the upload state file.

[Unreleased]: https://github.com/czarist/md2taiga/compare/b4b4cc4...HEAD
[0.3.0]: https://github.com/czarist/md2taiga/compare/cc638a9...b4b4cc4
[0.2.0]: https://github.com/czarist/md2taiga/compare/3d36ce1...cc638a9
[0.1.0]: https://github.com/czarist/md2taiga/commit/3d36ce1
