"""Validate user-story Markdown files and upload them to Taiga, each with its tasks.

Usage (from the repository root):
  python -X utf8 .claude/skills/taiga-stories/scripts/taiga_stories.py validate [file.md ...]
  python -X utf8 .claude/skills/taiga-stories/scripts/taiga_stories.py upload --sprint "Sprint 34" --dry-run
  TAIGA_TOKEN=... python -X utf8 .claude/skills/taiga-stories/scripts/taiga_stories.py upload --sprint "Sprint 34"
  TAIGA_TOKEN=... python -X utf8 .claude/skills/taiga-stories/scripts/taiga_stories.py upload --backlog

Configuration comes from .env at the repository root (see .env.example). Command-line
flags override it. The token is never read from .env: pass it per session in TAIGA_TOKEN.

Behaviour:
- Assignee: the token owner (users/me), on the story and on every task.
- Status: the project defaults (Taiga picks them).
- Points: the story's **Points:** header field, else TAIGA_POINTS, on the project's
  computable role (none if both are empty).
- Idempotent: stories whose title already exists in the project are skipped, and an
  interrupted run resumes the same story instead of creating a duplicate
  (state in <stories dir>/.taiga_state.json).
"""
import argparse, glob, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))

# ---------------------------------------------------------------- config

def load_env(path):
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"\'')
    return env


def parse_project_url(url):
    """https://host/project/<slug>[/...] -> (api base, slug)."""
    u = urllib.parse.urlparse(url)
    m = re.match(r'^/project/([^/]+)', u.path)
    if not u.scheme or not m:
        sys.exit('TAIGA_PROJECT_URL must look like https://<host>/project/<slug>, got: %r' % url)
    return '%s://%s/api/v1' % (u.scheme, u.netloc), m.group(1)

# ---------------------------------------------------------------- markdown

# Headings are accepted in English or Portuguese, so older stories keep working.
H1 = r'^#\s*(?:Story|História):\s*'
SECTIONS = [  # (name shown in messages, accepted headings)
    ('User story', ['User story', 'História de usuário']),
    ('Description', ['Description', 'Descrição']),
    ('Acceptance criteria', ['Acceptance criteria', 'Critérios de aceite']),
    ('Tasks', ['Tasks', 'Tarefas']),
    ('Notes', ['Deployment notes', 'Notes', 'Observações para implantação', 'Observações']),
]
FIELDS = [('Project', 'Projeto'), ('Branch', 'Branch'), ('Version', 'Versão'), ('Date', 'Período')]
TASKS_RX = r'^## (?:Tasks|Tarefas)\s*$(.*?)(?=^## |\Z)'


def read(path):
    return open(path, encoding='utf-8').read().replace('\r\n', '\n')


POINTS_RX = r'^\*\*(?:Points|Pontos):\*\*\s*(\S+)\s*$'


def story_points(path):
    """Value of the optional **Points:** / **Pontos:** header field, or None."""
    m = re.search(POINTS_RX, read(path), re.M)
    return m.group(1) if m else None


def parse(path):
    """-> (title, description = whole file minus H1, [{'subject', 'desc'}])."""
    txt = read(path)
    lines = txt.split('\n')
    title = re.sub(H1, '', lines[0]).lstrip('# ').strip()
    desc = '\n'.join(lines[1:]).strip()
    tasks, cur = [], None
    m = re.search(TASKS_RX, txt, re.M | re.S)
    for l in (m.group(1).split('\n') if m else []):
        mt = re.match(r'^\d+\.\s+\*\*(.+?)\*\*\s*(.*)$', l)
        if mt:
            cur = {'subject': mt.group(1).strip(), 'desc': [mt.group(2)] if mt.group(2) else []}
            tasks.append(cur)
        elif l.startswith('#'):
            cur = None
        elif cur is not None:
            cur['desc'].append(l.strip())
    for t in tasks:
        t['desc'] = '\n'.join(t['desc']).strip()
    return title, desc, tasks


def validate(path):
    """-> list of problems; entries starting with 'warning:' do not block the upload."""
    txt, name, probs = read(path), os.path.basename(path), []
    if not re.match(H1 + r'\S', txt):
        probs.append('first line must be "# Story: <title>"')
    if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*\.md$', name):
        probs.append('file name: lowercase, no accents, words-with-hyphens')
    for en, pt in FIELDS:
        if not re.search(r'^\*\*(%s|%s)s?:\*\*' % (en, pt), txt, re.M) and not (pt == 'Versão' and '**Versões:**' in txt):
            probs.append('missing header field **%s:**' % en)
    pos = []
    for label, heads in SECTIONS:
        p = min([i for i in (txt.find('\n## %s\n' % h) for h in heads) if i >= 0], default=-1)
        if p < 0:
            probs.append('missing section "## %s"' % label)
        else:
            pos.append(p)
    if pos != sorted(pos):
        probs.append('sections out of template order')
    if not re.search(r'\*\*(As|Como)\*\* .+\n\*\*(I want|quero)\*\* .+\n\*\*(so that|para)\*\* ', txt, re.I):
        probs.append('user story must be "**As** ... / **I want** ... / **so that** ..."')
    if not re.search(r'^- \[[ x]\] ', txt, re.M):
        probs.append('acceptance criteria must be a "- [ ] ..." checklist')
    _, _, tasks = parse(path)
    if not tasks:
        probs.append('no task in "1. **Title**" format under ## Tasks')
    m = re.search(TASKS_RX, txt, re.M | re.S)
    nums = [int(n) for n in re.findall(r'^(\d+)\.\s+\*\*', m.group(1), re.M)] if m else []
    if nums and nums != list(range(1, len(nums) + 1)):
        probs.append('task numbering must be continuous (1, 2, 3...) across groups')
    probs += ['warning: task without description: %s' % t['subject'] for t in tasks if not t['desc']]
    return probs

# ---------------------------------------------------------------- api

class Taiga:
    # Cloudflare in front of Taiga answers 403 with an HTML page ("Just a moment...") when
    # a text looks like SQL or HTML, e.g. "; `create.vue` ... `x`", "<script>", or
    # "Class::method" next to "GET /route". Retry with progressively plainer text.
    VARIANTS = [
        ('original', lambda s: s),
        ('";" -> "."', lambda s: s.replace(';', '.')),
        ('no backticks / <tags>', lambda s: re.sub(r'<(/?\w+)>', r'\1', s.replace(';', '.').replace('`', ''))),
        ('no "::"', lambda s: re.sub(r'<(/?\w+)>', r'\1', s.replace(';', '.').replace('`', '').replace('::', ' method '))),
        ('DESCRIPTION DROPPED', lambda s: ''),
    ]

    def __init__(self, base, token):
        self.base, self.token, self.adjusted = base, token, []

    def raw(self, method, path, body=None):
        req = urllib.request.Request(
            self.base + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json',
                     'x-disable-pagination': 'True'})
        with urllib.request.urlopen(req) as r:
            t = r.read().decode('utf-8')
            return json.loads(t) if t else None

    def send(self, method, path, body):
        """POST/PATCH with the firewall fallback on 'description'."""
        if not body.get('description'):
            return self.raw(method, path, body)
        for name, f in self.VARIANTS:
            b = dict(body, description=f(body['description']))
            try:
                r = self.raw(method, path, b)
                if name != 'original':
                    self.adjusted.append((body.get('subject'), name))
                return r
            except urllib.error.HTTPError as e:
                payload = e.read()
                if e.code != 403 or b'PermissionDenied' in payload:  # real permission error
                    raise
                time.sleep(1)
        raise RuntimeError('blocked by firewall: %s' % body.get('subject'))

# ---------------------------------------------------------------- commands

def files_in(directory, names):
    # a name is looked up in the stories dir; a path that exists as given is used as is
    pick = lambda f: f if os.path.exists(f) and os.path.dirname(f) else os.path.join(directory, f)
    return [pick(f) for f in names] or sorted(glob.glob(os.path.join(directory, '*.md')))


def cmd_validate(a):
    files = files_in(a.dir, a.files)
    bad = 0
    for f in files:
        p = validate(f)
        errors = [x for x in p if not x.startswith('warning')]
        bad += bool(errors)
        print(('OK    ' if not errors else 'ERROR ') + os.path.basename(f))
        for x in p:
            print('        -', x)
    print('\n%d of %d files with format errors.' % (bad, len(files)))
    return 1 if bad else 0


def cmd_upload(a):
    if bool(a.sprint) == a.backlog:
        sys.exit('Choose exactly one: --sprint "<name>" or --backlog.')
    files = files_in(a.dir, a.files)
    if a.dry_run:
        print('Target: %s' % (a.sprint or 'backlog'))
        for f in files:
            t, _, ts = parse(f)
            pts = story_points(f) or a.points or 'none'
            print('%s (%s pts, %d tasks)' % (t, pts, len(ts)))
            for x in ts:
                print('   -', x['subject'])
        return 0
    token = os.environ.get('TAIGA_TOKEN', '').strip().strip('"\'')
    if not token:
        sys.exit('Set TAIGA_TOKEN (in Taiga: F12 > Console > localStorage.getItem("token")).')

    base, slug = parse_project_url(a.project_url)
    api = Taiga(base, token)
    me = api.raw('GET', '/users/me')['id']
    proj = api.raw('GET', '/projects/by_slug?slug=' + slug)
    pid = proj['id']
    milestone = None
    if a.sprint:
        milestone = next((m['id'] for m in api.raw('GET', '/milestones?project=%d' % pid) if m['name'] == a.sprint), None)
        if not milestone:
            sys.exit('Sprint "%s" not found in project %s.' % (a.sprint, slug))
    # points: the story's **Points:** field, else --points / TAIGA_POINTS, else none
    role = next((r['id'] for r in proj['roles'] if r['computable']), None)
    scale = {p['name']: p['id'] for p in proj['points']}
    def points_for(f):
        value = story_points(f) or a.points
        if not value or role is None:
            return None
        if value not in scale:
            sys.exit('%s: point value "%s" not in project scale %s' % (os.path.basename(f), value, list(scale)))
        return {str(role): scale[value]}
    for f in files:  # fail before creating anything
        points_for(f)

    state_path = os.path.join(a.dir, '.taiga_state.json')
    state = json.load(open(state_path, encoding='utf-8')) if os.path.exists(state_path) else {}
    save = lambda: json.dump(state, open(state_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    existing = {u['subject'].strip(): u['ref'] for u in api.raw('GET', '/userstories?project=%d' % pid)}
    created = []

    for f in files:
        key = '%s|%s' % (slug, os.path.basename(f))
        rec = state.get(key)
        title, desc, tasks = parse(f)
        if rec and rec.get('done'):
            print('already uploaded: %s' % title)
            continue
        if not rec and title in existing and not a.force:
            print('exists in project (#%d), skipped: %s' % (existing[title], title))
            continue
        if rec:  # interrupted run: finish the same story
            us_id = rec['us_id']
            skip = len(api.raw('GET', '/tasks?user_story=%d' % us_id))
        else:
            body = {'project': pid, 'subject': title, 'description': desc, 'assigned_to': me, 'milestone': milestone}
            points = points_for(f)
            if points:
                body['points'] = points
            us_id = api.send('POST', '/userstories', body)['id']
            skip = 0
            state[key] = {'us_id': us_id, 'done': False}
            save()
        for t in tasks[skip:]:
            time.sleep(0.5)
            api.send('POST', '/tasks', {'project': pid, 'user_story': us_id, 'milestone': milestone,
                                        'subject': t['subject'], 'description': t['desc'], 'assigned_to': me})
        state[key]['done'] = True
        save()
        ref = api.raw('GET', '/userstories/%d' % us_id)['ref']
        created.append(ref)
        print('#%d %s (%d tasks)' % (ref, title, len(tasks)), flush=True)

    print('\nCreated or completed %d stories in %s.' % (len(created), a.sprint or 'backlog'))
    if api.adjusted:
        print('Texts rewritten because of the firewall:')
        for s, n in api.adjusted:
            print('  - %s -> %s' % (s, n))
    return 0


def main():
    env = load_env(os.path.join(ROOT, '.env'))
    ap = argparse.ArgumentParser(description='Validate and upload user stories to Taiga.')
    ap.add_argument('--dir', default=os.path.join(ROOT, env.get('STORIES_DIR', 'stories')))
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('validate', help='check story format (no network)')
    v.add_argument('files', nargs='*')
    u = sub.add_parser('upload', help='create stories and tasks in Taiga')
    u.add_argument('--project-url', default=env.get('TAIGA_PROJECT_URL', ''))
    u.add_argument('--sprint', help='exact sprint name, e.g. "Sprint 34"')
    u.add_argument('--backlog', action='store_true', help='leave stories in the backlog')
    u.add_argument('--points', default=env.get('TAIGA_POINTS', ''), help='point value name, empty = none')
    u.add_argument('--dry-run', action='store_true', help='show what would be created')
    u.add_argument('--force', action='store_true', help='create even if the title already exists')
    u.add_argument('files', nargs='*')
    a = ap.parse_args()
    if a.cmd == 'upload' and not a.dry_run and not a.project_url:
        sys.exit('Set TAIGA_PROJECT_URL in .env (copy .env.example) or pass --project-url.')
    sys.exit(cmd_validate(a) if a.cmd == 'validate' else cmd_upload(a))


if __name__ == '__main__':
    main()
