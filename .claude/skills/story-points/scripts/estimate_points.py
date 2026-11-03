"""Suggest story points (1, 2, 3, 5, 8, 13, 21) for story .md files from the code repository's git history.

Usage (from the md2taiga repository root):
  python -X utf8 .claude/skills/story-points/scripts/estimate_points.py [story.md ...]
      [--repo PATH] [--since YYYY-MM-DD] [--commits sha1,sha2] [--json]

- The code repository comes from --repo or CODE_REPO_PATH in .env.
- Commits are searched on the branch named in the story's **Branch:** field (or HEAD).
- A commit matches a story when it touches files the story mentions in `backticks`, or
  when its subject shares words with the story title. --commits overrides the matching.
- The suggestion is a heuristic: the agent must review it and the user confirms it.
"""
import argparse, glob, json, os, re, subprocess, sys, unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
SCALE = [1, 2, 3, 5, 8, 13, 21]
# code lines changed -> base points (upper bound of each band)
BANDS = [(30, 1), (100, 2), (250, 3), (600, 5), (1500, 8), (3000, 13)]
IGNORED = re.compile(r'(changelog|versao\.txt|version\.txt|package-lock\.json|composer\.lock|yarn\.lock|'
                     r'pnpm-lock\.yaml|/public/build/|/dist/|\.min\.(js|css)$|\.map$|\.(png|jpe?g|gif|svg|ico|pdf)$)', re.I)
AREAS = [  # (area, path regex)
    ('tests', r'(^|/)tests?/|\.(test|spec)\.\w+$|Test\.php$'),
    ('migrations', r'(^|/)migrations?/'),
    ('frontend', r'\.(vue|jsx?|tsx?|css|scss|blade\.php)$'),
    ('infra', r'(Dockerfile|docker-compose|\.ya?ml$|\.env|nginx|/config/)'),
    ('backend', r'\.(php|py|go|rb|java|cs)$'),
]
RISKY = re.compile(r'(auth|login|perm|perfil|role|polic|security|token|migration|lgpd)', re.I)
STOP = set('''para com sem uma umas uns que por dos das nos nas pelo pela pelos pelas como mais quando ser
seu sua seus suas este esta esse essa isso nao sim entre sobre ate tela telas pagina paginas novo nova
the and for with from into when that this page story fix feat chore docs perf historia correcao'''.split())


def env_value(key):
    path = os.path.join(ROOT, '.env')
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            if line.strip().startswith(key + '='):
                return line.split('=', 1)[1].strip().strip('"\'')
    return ''


def norm(s):
    s = unicodedata.normalize('NFKD', s.lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


def words(s):
    return {w for w in re.findall(r'[a-z0-9]{4,}', norm(s)) if w not in STOP}


def read_story(path):
    txt = open(path, encoding='utf-8').read().replace('\r\n', '\n')
    title = re.sub(r'^#\s*(?:Story|História):\s*', '', txt.split('\n')[0]).strip()
    branch = re.search(r'^\*\*Branch:\*\*\s*`?([^`\s]+)`?', txt, re.M)
    tasks = re.findall(r'^\d+\.\s+\*\*(.+?)\*\*', txt, re.M)
    # names in backticks that look like files or classes: footer.blade.php, MenuService, useX.js
    names = set()
    for code in re.findall(r'`([^`\n]+)`', txt):
        for tok in re.split(r'[\s,()]+', code):
            tok = tok.strip('/.:;').split('::')[0]
            base = tok.split('/')[-1]
            if re.search(r'\.\w{1,5}$', base) or re.match(r'^[A-Z][a-z]+[A-Z]\w+$', base):
                if len(base) >= 5 and not re.match(r'^\d', base):
                    names.add(base.lower())
    return {'title': title, 'branch': branch.group(1) if branch else None, 'tasks': tasks,
            'names': names, 'words': words(title), 'task_words': words(' '.join(tasks))}


def git_log(repo, ref, since):
    cmd = ['git', '-C', repo, 'log', ref, '--no-merges', '--date=short', '--numstat',
           '--format=\x1e%H\x1f%ad\x1f%s']
    if since:
        cmd.append('--since=' + since)
    out = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if out.returncode:
        sys.exit('git log failed: ' + out.stderr.strip())
    commits = []
    for chunk in out.stdout.split('\x1e')[1:]:
        head, *rest = chunk.strip('\n').split('\n')
        sha, date, subject = head.split('\x1f')
        files = []
        for l in rest:
            p = l.split('\t')
            if len(p) == 3:
                add = int(p[0]) if p[0].isdigit() else 0
                rem = int(p[1]) if p[1].isdigit() else 0
                files.append((p[2], add, rem))
        commits.append({'sha': sha[:7], 'date': date, 'subject': subject, 'files': files})
    return commits


def name_in(path, name):
    """File names (with extension) must match the end of the path. Class names
    (MenuService) match a file whose name starts with them (MenuService.php)."""
    path = norm(path)
    if '.' in name:
        return path == name or path.endswith('/' + name)
    return ('/' + name) in path


def touches(c, name):
    return any(name_in(f[0], name) for f in c['files'])


def match(story, c, rare):
    """-> (score, kind, file hits, title hits). kind: 'title' (subject matches the title),
    'files' (touches >= 2 files that the story names and few commits touch) or None."""
    file_hits = {n for n in story['names'] if touches(c, n)}
    rare_hits = file_hits & rare
    sw = words(c['subject'])
    title_hits = story['words'] & sw
    task_hits = (story['task_words'] - story['words']) & sw
    score = 3 * len(rare_hits) + len(file_hits) + 2 * len(title_hits) + min(len(task_hits), 3)
    need = 2 if len(story['words']) >= 3 else 1
    kind = 'title' if len(title_hits) >= need else 'files' if len(rare_hits) >= 2 else None
    return score, kind, sorted(file_hits), sorted(title_hits)


def metrics(story, commits, shared):
    """Lines and areas of the chosen commits. In a commit shared with other stories, count
    only the files this story mentions (and their tests)."""
    files = {}
    for c in commits:
        for path, add, rem in c['files']:
            if IGNORED.search(path):
                continue
            if c['sha'] in shared or c.get('kind') == 'partial':
                stems = {n.split('.')[0] for n in story['names']}
                # keep named files and their tests (MenuService -> MenuServiceTest)
                if not any(name_in(path, n) for n in story['names']) and \
                        not any(s in norm(path) for s in stems if len(s) >= 8 and 'test' in norm(path)):
                    continue
            f = files.setdefault(path, [0, 0])
            f[0] += add
            f[1] += rem
    lines = sum(a + r for a, r in files.values())
    areas = sorted({a for p in files for a, rx in AREAS if re.search(rx, p, re.I)})
    new_files = sum(1 for a, r in files.values() if r == 0 and a > 0)
    risky = sorted({m.group(1).lower() for p in files for m in [RISKY.search(p)] if m})
    return {'files': len(files), 'lines': lines, 'new_files': new_files, 'areas': areas, 'risky': risky}


def suggest(m, n_commits):
    if not n_commits:
        return None, ['no matching commit: estimate from the story text and ask the user']
    base = next((p for limit, p in BANDS if m['lines'] <= limit), 21)
    i, why = SCALE.index(base), ['%d code lines in %d files -> %d' % (m['lines'], m['files'], base)]
    code_areas = [a for a in m['areas'] if a != 'tests']
    if len(code_areas) >= 3:
        i += 1
        why.append('touches %s -> +1 step' % ', '.join(code_areas))
    if 'migrations' in m['areas'] or m['risky']:
        i += 1
        why.append('risk (%s) -> +1 step' % ', '.join(m['risky'] or ['migrations']))
    if m['lines'] > 50 and 'tests' not in m['areas']:
        why.append('no tests touched: consider uncertainty')
    return SCALE[min(i, len(SCALE) - 1)], why


def main():
    ap = argparse.ArgumentParser(description='Suggest story points from git history.')
    ap.add_argument('stories', nargs='*')
    ap.add_argument('--repo', default=env_value('CODE_REPO_PATH'))
    ap.add_argument('--since', default='')
    ap.add_argument('--commits', default='', help='comma-separated SHAs to use instead of matching')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    if not a.repo or not os.path.isdir(a.repo):
        sys.exit('Set CODE_REPO_PATH in .env or pass --repo <path to the code repository>.')
    sdir = os.path.join(ROOT, env_value('STORIES_DIR') or 'stories')
    files = [f if os.path.exists(f) and os.path.dirname(f) else os.path.join(sdir, f) for f in a.stories] \
        or sorted(glob.glob(os.path.join(sdir, '*.md')))

    stories = [dict(read_story(f), file=os.path.basename(f)) for f in files]
    logs = {}
    for s in stories:
        ref = s['branch'] or 'HEAD'
        if ref not in logs:
            ok = subprocess.run(['git', '-C', a.repo, 'rev-parse', '--verify', '-q', ref], capture_output=True).returncode == 0
            logs[ref] = git_log(a.repo, ref if ok else 'HEAD', a.since)
        s['log'] = logs[ref]
    forced = [x.strip()[:7] for x in a.commits.split(',') if x.strip()]
    for s in stories:
        # a named file is "rare" when at most 3 commits of the log touch it
        rare = {n for n in s['names'] if sum(touches(c, n) for c in s['log']) <= 3}
        cands = []
        for c in s['log']:
            score, kind, fh, th = match(s, c, rare)
            if (forced and c['sha'] in forced) or (not forced and kind):
                cands.append(dict(c, score=score, kind=kind, file_hits=fh, title_hits=th))
        # commits whose subject matches the title win, file-only matches are the fallback
        if not forced and any(c['kind'] == 'title' for c in cands):
            cands = [c for c in cands if c['kind'] == 'title']
        if not forced and not cands:
            # last resort: small changes bundled into bigger commits. Take the commits that
            # touch named files (rare ones first) and count only those files.
            weak = []
            for c in s['log']:
                score, _, fh, th = match(s, c, rare)
                if fh:
                    weak.append(dict(c, score=score, kind='partial', file_hits=fh, title_hits=th,
                                     rare_hits=set(fh) & rare))
            if any(c['rare_hits'] for c in weak):  # commits touching rare files only
                weak = [c for c in weak if c['rare_hits']]
            cands = sorted(weak, key=lambda c: -c['score'])[:3]
        s['commits'] = sorted(cands, key=lambda c: -c['score'])
    owners = {}
    for s in stories:
        for c in s['commits']:
            owners.setdefault(c['sha'], set()).add(s['file'])
    shared = {sha for sha, o in owners.items() if len(o) > 1}

    out = []
    for s in stories:
        m = metrics(s, s['commits'], shared)
        pts, why = suggest(m, len(s['commits']))
        out.append({'file': s['file'], 'title': s['title'], 'suggested': pts, 'why': why, 'metrics': m,
                    'commits': [{'sha': c['sha'], 'date': c['date'], 'subject': c['subject'],
                                 'shared': c['sha'] in shared, 'kind': c.get('kind'), 'file_hits': c['file_hits'],
                                 'title_hits': c['title_hits']} for c in s['commits']]})
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    for r in out:
        print('\n%s  ->  %s pts' % (r['title'], r['suggested'] or '?'))
        print('  file: %s' % r['file'])
        for c in r['commits'][:8]:
            tag = '  [partial: only named files]' if c['kind'] == 'partial' else '  [shared]' if c['shared'] else ''
            print('  %s %s %s%s' % (c['sha'], c['date'], c['subject'][:80], tag))
        if len(r['commits']) > 8:
            print('  ... %d more commits' % (len(r['commits']) - 8))
        for w in r['why']:
            print('  - ' + w)


if __name__ == '__main__':
    main()
