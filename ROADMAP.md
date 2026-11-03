# Roadmap

What md2taiga does today, and what could come next. Finished phases list their version in the [changelog](CHANGELOG.md). The later phases are ideas in rough order of value, with no dates.

## Done

### Phase 1 — Upload stories to Taiga (0.1.0)

- [x] One Markdown file per story, with a fixed structure and a template
- [x] `validate`: offline format check
- [x] `upload` to a sprint or to the backlog, through the Taiga REST API, with no dependencies
- [x] Any Taiga project, configured by its link in `.env`
- [x] Token read only from the environment, asked for on every upload
- [x] No duplicates: existing titles are skipped and interrupted runs resume
- [x] Firewall (WAF) fallback that rewrites blocked text and reports it
- [x] English and Portuguese headings
- [x] `taiga-stories` Claude Code skill and `AGENTS.md`

### Phase 2 — Points per story (0.2.0)

- [x] `**Points:**` field on each story, with no global default
- [x] Upload stops before creating anything if a story has no valid points
- [x] The agent asks for missing points before saving or uploading

### Phase 3 — Estimate points from git history (0.3.0)

- [x] `story-points` skill and `estimate_points.py`
- [x] Commit matching by title, by rarely touched files named in the story, and by commits shared between stories
- [x] Suggestion on the 1, 2, 3, 5, 8, 13, 21 scale, from code size, areas touched and risk
- [x] Agent reviews the evidence and the user confirms

## Next

### Phase 4 — Quality

- [ ] Unit tests for the parser, the validator, the firewall fallback and the commit matching
- [ ] GitHub Actions workflow running the tests and `validate` on the template, plus a CI badge in the README
- [ ] `--version` flag, with the version kept in one place
- [ ] License file

### Phase 5 — Better estimates

- [ ] Calibrate the size bands per project from stories that already have points, in Taiga or in `stories/`
- [ ] Configurable bands and risk patterns in `.env`
- [ ] Read uncommitted work (`git diff`) for stories that are still in progress
- [ ] Use the version bump (changelog, version file) as a matching signal

### Phase 6 — Richer sync with Taiga

- [ ] Update stories that already exist instead of skipping them, with the diff shown first
- [ ] Mark tasks as closed from the checked acceptance criteria, or from a status field
- [ ] Tags, epics and story status from header fields
- [ ] Choose the points role when a project has more than one computable role
- [ ] Pull stories from Taiga into `.md` files

### Phase 7 — Distribution

- [ ] Installable package (`pipx install md2taiga`) with an `md2taiga` command
- [ ] Interactive token prompt (`getpass`) as an alternative to the environment variable
- [ ] Several projects in one checkout (one `.env` section or folder per project)
