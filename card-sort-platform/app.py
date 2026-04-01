import csv
import functools
import io
import json
import os
import random
import uuid
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from flask import (Flask, jsonify, redirect, render_template,
                   request, send_file, session, url_for)

from supabase_client import supabase as sb

# ── APP SETUP ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'uxr-card-sort-dev-key')

DASHBOARD_PASSWORD = os.environ.get('DASHBOARD_PASSWORD', 'Lexipol123')


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('auth'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ── CARD DATA ─────────────────────────────────────────────────────────────────

CARDS = [
    {'id': 'P1',  'label': 'Update policy or procedure manual content'},
    {'id': 'P2',  'label': 'Assign policy-related trainings to users'},
    {'id': 'P3',  'label': 'Review regulatory policy updates'},
    {'id': 'P4',  'label': 'Review policy acknowledgement records'},
    {'id': 'P5',  'label': 'Review accreditation requirements'},
    {'id': 'T1',  'label': 'Assign trainings to users'},
    {'id': 'T2',  'label': 'Create learning plans'},
    {'id': 'T3',  'label': 'Review training phase progress'},
    {'id': 'T4',  'label': 'View certification expiration records'},
    {'id': 'T5',  'label': 'Audit training reports'},
    {'id': 'W1',  'label': 'Manage peer support and help line contacts'},
    {'id': 'W2',  'label': 'Create health and well-being resources'},
    {'id': 'W3',  'label': 'Send notifications to users about resources'},
    {'id': 'W4',  'label': 'Review engagement analytics for wellness programs'},
    {'id': 'W5',  'label': 'Create wellness and development events'},
    {'id': 'PR1', 'label': 'Configure data collection forms'},
    {'id': 'PR2', 'label': 'Configure monitoring rules'},
    {'id': 'PR3', 'label': 'View and export analytics'},
    {'id': 'PR4', 'label': 'Configure form review workflows'},
    {'id': 'PR5', 'label': 'Review flagged records'},
]

CARDS_BY_ID = {c['id']: c for c in CARDS}

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _fmt_time(seconds):
    if not seconds:
        return '—'
    m, s = divmod(int(seconds), 60)
    return f'{m}:{s:02d}'


def _save_session_json(sess, assignments_data, categories_data):
    """Write a local JSON snapshot of the completed session as a backup."""
    out_dir = os.path.join(os.path.dirname(__file__), 'data', 'sessions')
    os.makedirs(out_dir, exist_ok=True)
    token = sess.get('token', 'unknown')
    fname = f"session_{token}_{datetime.now().strftime('%Y%m%d')}.json"
    data  = {
        **sess,
        'assignments': assignments_data,
        'categories':  categories_data,
    }
    with open(os.path.join(out_dir, fname), 'w') as f:
        json.dump(data, f, indent=2, default=str)


def _agreement_matrix(all_assignments, session_ids):
    """
    Build the card-placement matrix from a pre-fetched list of assignment dicts.
    Returns (matrix, all_cats).
    """
    n = len(session_ids)
    if n == 0:
        return [], []

    all_cats = sorted(set(a['category'] for a in all_assignments))

    matrix = []
    for card in CARDS:
        card_asgns = [a for a in all_assignments if a['card_id'] == card['id']]
        row = {
            'card_id':      card['id'],
            'card_label':   card['label'],
            'distribution': {},
            'agreement_pct': 0,
            'top_category': None,
        }
        max_count = 0
        for cat in all_cats:
            count = sum(1 for a in card_asgns if a['category'] == cat)
            pct   = round((count / n) * 100)
            row['distribution'][cat] = {'count': count, 'pct': pct}
            if count > max_count:
                max_count = count
                row['top_category'] = cat
        row['agreement_pct'] = round((max_count / n) * 100) if n else 0
        matrix.append(row)

    return matrix, all_cats


# ── PARTICIPANT ROUTES ────────────────────────────────────────────────────────

@app.route('/join', methods=['POST'])
def join():
    """Public: auto-create a session and redirect the participant to their sort URL."""
    token = str(uuid.uuid4())[:8]
    sb.table('sessions').insert({'token': token}).execute()
    return redirect(url_for('sort', token=token))


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/sort/<token>')
def sort(token):
    res  = sb.table('sessions').select('*').eq('token', token).execute()
    sess = res.data[0] if res.data else None

    if not sess:
        return render_template('error.html', message='Session link not found.'), 404

    if sess['status'] == 'completed':
        return render_template('done.html', already_done=True,
                               participant_name=sess['participant_name'])

    # Persist card order so a refresh doesn't re-shuffle
    if sess['card_order']:
        ordered_ids = json.loads(sess['card_order'])
        cards = [CARDS_BY_ID[cid] for cid in ordered_ids if cid in CARDS_BY_ID]
    else:
        cards = CARDS.copy()
        random.shuffle(cards)
        ordered_ids = [c['id'] for c in cards]
        sb.table('sessions') \
          .update({'card_order': json.dumps(ordered_ids)}) \
          .eq('token', token) \
          .execute()

    return render_template(
        'sort.html',
        token=token,
        cards_json=json.dumps(cards),
        participant_name=sess['participant_name'] or '',
    )


@app.route('/api/session/start', methods=['POST'])
def api_session_start():
    data  = request.get_json(force=True)
    token = data.get('token', '').strip()
    name  = data.get('name', '').strip() or 'Anonymous'

    if not token:
        return jsonify({'error': 'Missing token'}), 400

    sb.table('sessions').update({
        'participant_name': name,
        'status':           'in_progress',
        'started_at':       datetime.utcnow().isoformat(),
    }).eq('token', token).execute()

    return jsonify({'ok': True})


@app.route('/api/session/submit', methods=['POST'])
def api_session_submit():
    data       = request.get_json(force=True)
    token      = data.get('token', '').strip()
    asgn_input = data.get('assignments', [])
    cat_input  = data.get('categories', [])
    duration   = data.get('duration_seconds', 0)

    if not token:
        return jsonify({'error': 'Missing token'}), 400

    res       = sb.table('sessions').select('id,status,token').eq('token', token).execute()
    sess_row  = res.data[0] if res.data else None

    if not sess_row:
        return jsonify({'error': 'Session not found'}), 404

    if sess_row['status'] == 'completed':
        return jsonify({'ok': True, 'already_submitted': True})

    sid = sess_row['id']

    asgn_records = [
        {
            'session_id':      sid,
            'card_id':         a.get('card_id'),
            'card_label':      a.get('card_label'),
            'category':        a.get('category', 'Unsorted'),
            'confidence':      a.get('confidence'),
            'time_seconds':    a.get('time_seconds'),
            'emotional_signal': a.get('emotional_signal', 'neutral'),
        }
        for a in asgn_input
    ]
    if asgn_records:
        sb.table('assignments').insert(asgn_records).execute()

    cat_records = [
        {
            'session_id':     sid,
            'name':           c.get('name'),
            'is_user_created': bool(c.get('is_user_created', False)),
            'card_count':     c.get('card_count', 0),
        }
        for c in cat_input
    ]
    if cat_records:
        sb.table('categories').insert(cat_records).execute()

    sb.table('sessions').update({
        'status':           'completed',
        'completed_at':     datetime.utcnow().isoformat(),
        'duration_seconds': duration,
    }).eq('id', sid).execute()

    # Local JSON backup — fetch fresh session row so backup has all fields
    sess_full = sb.table('sessions').select('*').eq('id', sid).execute().data[0]
    _save_session_json(sess_full, asgn_records, cat_records)

    return jsonify({'ok': True})


@app.route('/done')
def done():
    return render_template('done.html', already_done=False, participant_name='')


# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == DASHBOARD_PASSWORD:
            session['auth'] = True
            return redirect(url_for('dashboard'))
        error = 'Incorrect password'
    return render_template('login.html', error=error)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── RESEARCHER / DASHBOARD ROUTES ─────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    # Fetch sessions; embed assignments just to count them in one round-trip
    res      = sb.table('sessions') \
                 .select('*, assignments(id)') \
                 .order('created_at', desc=True) \
                 .execute()
    sessions = res.data
    for s in sessions:
        s['card_count']   = len(s.pop('assignments', []))
        s['duration_fmt'] = _fmt_time(s.get('duration_seconds'))
    return render_template('dashboard.html', sessions=sessions, base_url=request.host_url)


@app.route('/dashboard/create-session', methods=['POST'])
@login_required
def create_session():
    token = str(uuid.uuid4())[:8]
    sb.table('sessions').insert({'token': token}).execute()
    sort_url = request.host_url + f'sort/{token}'
    return jsonify({'token': token, 'url': sort_url})


@app.route('/dashboard/delete-session/<int:sid>', methods=['POST'])
@login_required
def delete_session(sid):
    # ON DELETE CASCADE in the schema handles assignments + categories automatically
    sb.table('sessions').delete().eq('id', sid).execute()
    return jsonify({'ok': True})


# ── API: LIVE STATS ───────────────────────────────────────────────────────────

@app.route('/api/stats')
@login_required
def api_stats():
    res      = sb.table('sessions') \
                 .select('*, assignments(id)') \
                 .order('created_at', desc=True) \
                 .execute()
    sessions = res.data

    for s in sessions:
        s['card_count'] = len(s.pop('assignments', []))

    total     = len(sessions)
    completed = sum(1 for s in sessions if s['status'] == 'completed')
    in_prog   = sum(1 for s in sessions if s['status'] == 'in_progress')
    durations = [s['duration_seconds'] for s in sessions
                 if s['status'] == 'completed' and s['duration_seconds']]
    avg_dur   = sum(durations) / len(durations) if durations else None

    return jsonify({
        'total':        total,
        'completed':    completed,
        'in_progress':  in_prog,
        'avg_duration': _fmt_time(avg_dur),
        'sessions':     sessions,
    })


# ── API: ANALYSIS ─────────────────────────────────────────────────────────────

@app.route('/api/analysis')
@login_required
def api_analysis():
    rows        = sb.table('sessions').select('id').eq('status', 'completed').execute()
    session_ids = [r['id'] for r in rows.data]
    n           = len(session_ids)

    if n == 0:
        return jsonify({'matrix': [], 'all_cats': [], 'categories': [], 'n': 0})

    # Fetch all assignments for completed sessions in one query
    asgn_res        = sb.table('assignments') \
                        .select('session_id,card_id,category') \
                        .in_('session_id', session_ids) \
                        .execute()
    all_assignments = asgn_res.data

    # Fetch category records to detect user-created groups
    cats_res        = sb.table('categories') \
                        .select('name,is_user_created,session_id') \
                        .in_('session_id', session_ids) \
                        .execute()
    all_cat_records = cats_res.data

    matrix, all_cats = _agreement_matrix(all_assignments, session_ids)

    # Category usage — derived from already-fetched assignment data
    session_ids_set = set(session_ids)
    cat_usage = []
    for cat in all_cats:
        sessions_using = {a['session_id'] for a in all_assignments if a['category'] == cat}
        used_by = len(sessions_using)
        is_new  = any(
            c['is_user_created'] and c['name'] == cat
            for c in all_cat_records
        )
        cat_usage.append({
            'name':            cat,
            'sessions_used':   used_by,
            'pct':             round((used_by / n) * 100),
            'is_user_created': is_new,
        })

    cat_usage.sort(key=lambda x: x['sessions_used'], reverse=True)

    return jsonify({
        'n':          n,
        'all_cats':   all_cats,
        'matrix':     matrix,
        'categories': cat_usage,
    })


# ── EXPORT ────────────────────────────────────────────────────────────────────

@app.route('/api/export/json')
@login_required
def export_json():
    # Fetch completed sessions with their assignments and categories embedded
    res      = sb.table('sessions') \
                 .select('*, assignments(*), categories(*)') \
                 .eq('status', 'completed') \
                 .execute()

    buf = io.BytesIO(json.dumps(res.data, indent=2, default=str).encode())
    buf.seek(0)
    return send_file(buf, mimetype='application/json', as_attachment=True,
                     download_name=f'card-sort-{datetime.now().strftime("%Y%m%d")}.json')


@app.route('/api/export/csv')
@login_required
def export_csv():
    # Fetch completed sessions
    sess_res = sb.table('sessions') \
                 .select('id,token,participant_name,role,duration_seconds') \
                 .eq('status', 'completed') \
                 .execute()
    sess_map = {s['id']: s for s in sess_res.data}

    buf    = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['session_token', 'participant_name', 'role', 'duration_seconds',
                     'card_id', 'card_label', 'assigned_category',
                     'confidence', 'time_seconds', 'emotional_signal'])

    if sess_map:
        asgn_res = sb.table('assignments') \
                     .select('*') \
                     .in_('session_id', list(sess_map.keys())) \
                     .order('session_id') \
                     .execute()
        for a in asgn_res.data:
            s = sess_map[a['session_id']]
            writer.writerow([
                s['token'], s['participant_name'], s['role'], s['duration_seconds'],
                a['card_id'], a['card_label'], a['category'],
                a['confidence'], a['time_seconds'], a['emotional_signal'],
            ])

    buf.seek(0)
    bytes_buf = io.BytesIO(buf.read().encode())
    bytes_buf.seek(0)
    return send_file(bytes_buf, mimetype='text/csv', as_attachment=True,
                     download_name=f'card-sort-{datetime.now().strftime("%Y%m%d")}.csv')


# ── ERRORS ────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', message='Page not found.'), 404


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f'\n🗂️  Card Sort Platform running at http://localhost:{port}')
    print(f'📊  Researcher dashboard: http://localhost:{port}/dashboard\n')
    app.run(debug=True, port=port)
