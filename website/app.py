"""Compunet Reborn — Website (Registration + Account Management)"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from urllib.parse import urlencode

import requests
from flask import (Flask, Response, flash, get_flashed_messages, redirect,
                   render_template, request, session, url_for)

import config

app = Flask(__name__)
app.secret_key = config.get('WEBSITE_SECRET_KEY', 'dev-secret-change-me')

# ⚠ The site's only file upload is a directory header frame, which may not
# exceed 512 bytes. Cap the request body well below anything worth buffering so
# an oversized or hostile POST is refused by Flask before a handler sees it.
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024

# ============================================================
# Session cookie policy
#
# ⚠ Set explicitly rather than inherited. Browsers now default cookies to
# SameSite=Lax, which does block a cross-site POST from carrying the session — so
# the forms here were protected in practice by a default the site never stated.
# Relying on that is not a control: it is invisible, it varies by browser, and
# Lax deliberately still sends cookies on top-level GET navigation, which is why
# the two admin routes that changed state on GET were genuinely exposed (they are
# POST now).
#
# SECURE follows the scheme the site is actually published on. Hardcoding True
# breaks a local checkout — the cookie is never sent over http://localhost, so
# login silently fails and looks like a broken password. Hardcoding False ships a
# session cookie that will travel in clear.
# ============================================================
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = config.get(
    'WEBSITE_BASE_URL', 'http://localhost:6464').strip().lower().startswith('https://')

_version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
if not os.path.exists(_version_file):
    _version_file = os.path.join(os.path.dirname(__file__), '..', 'VERSION')
APP_VERSION = open(_version_file).read().strip() if os.path.exists(_version_file) else 'unknown'


# ⚠ Per-deployment, NOT hardcoded. dev.compunet.live must point at the dev
# client (connect-dev.compunet.live) and production at its own, or the dev site
# quietly sends testers to the live service. Unset means "no hosted client
# here", and the templates simply omit the link — which is the correct state
# for a deployment that has not published one yet.
CLIENT_URL = config.get('COMPUNET_CLIENT_URL', '').strip().rstrip('/')


@app.context_processor
def inject_version():
    return {'version': APP_VERSION, 'client_url': CLIENT_URL,
            'csrf_token': _csrf_token}


# ============================================================
# CSRF
#
# A cross-site request forgery is a page on another site causing YOUR browser to
# send a request here. The browser attaches the session cookie based on where the
# request is going, not where it came from, so the server sees a properly
# authenticated request and obeys — and the attacker never needs to read the
# reply, because the damage is the side effect.
#
# The defence is a secret the other site cannot obtain: a token this site issues,
# puts in its own forms, and checks on submission.
#
# ⚠ Checked centrally, in before_request, NOT per handler. This codebase has
# already been bitten by the other approach: `_api_check_auth` is called by hand
# at the top of every API handler, and the one that forgot it shipped unguarded
# (see the ⚠ on POST /api/audit). A new form here cannot forget a check it does
# not have to remember.
# ============================================================

def _csrf_token():
    """The token for this session, minted on first use."""
    token = session.get('_csrf')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf'] = token
    return token


@app.before_request
def _check_csrf():
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return None
    sent = request.form.get('_csrf') or request.headers.get('X-CSRF-Token', '')
    expected = session.get('_csrf', '')
    # compare_digest, not ==, so a wrong token cannot be discovered one character
    # at a time from how long the comparison takes.
    if not expected or not sent or not hmac.compare_digest(str(sent), str(expected)):
        app.logger.warning('CSRF check failed for %s %s from %s',
                           request.method, request.path, _client_ip())
        flash('That form could not be submitted — it was probably left open too '
              'long. Please try again.', 'error')
        return redirect(url_for('account') if 'user_id' in session
                        else url_for('login'))
    return None

USERID_RE = re.compile(r'^[A-Z0-9]{1,8}$')
PASSWORD_RE = re.compile(r'^[A-Z0-9]{1,6}$')


# ============================================================
# Helpers
# ============================================================

def _api_headers():
    return {
        'Authorization': f'Bearer {config.get("COMPUNET_API_KEY")}',
        'Content-Type': 'application/json',
    }


def _api_get(path):
    return requests.get(f'{config.get("COMPUNET_API_URL", "http://localhost:6403")}{path}', headers=_api_headers())


def _api_post(path, data):
    return requests.post(f'{config.get("COMPUNET_API_URL", "http://localhost:6403")}{path}', headers=_api_headers(), json=data)


def _api_put(path, data):
    return requests.put(f'{config.get("COMPUNET_API_URL", "http://localhost:6403")}{path}', headers=_api_headers(), json=data)


def _api_delete(path):
    return requests.delete(f'{config.get("COMPUNET_API_URL", "http://localhost:6403")}{path}', headers=_api_headers())


def _api_delete_json(path, data):
    """DELETE carrying a body — the server needs to know WHICH user is asking,
    because the API key identifies the website, not a person."""
    return requests.delete(f'{config.get("COMPUNET_API_URL", "http://localhost:6403")}{path}', headers=_api_headers(), json=data)


def _api_create_pending(data):
    return requests.post(
        f'{config.get("COMPUNET_API_URL", "http://localhost:6403")}/api/pending',
        headers=_api_headers(), json=data)


def _api_consume_pending(token, outcome='rejected'):
    """Retrieve and delete a pending registration.

    ⚠ `outcome` matters. This one endpoint serves BOTH approval and rejection:
    approving consumes the token and then creates the account, rejecting consumes
    it and creates nothing. Without being told, the server cannot distinguish them
    and would record every approval as a rejection as well.

    Both current callers are approvals — the admin button, and the user following
    their own verification link."""
    return requests.delete(
        f'{config.get("COMPUNET_API_URL", "http://localhost:6403")}/api/pending/{token}'
        f'?outcome={outcome}',
        headers=_api_headers())


def _send_email(to, subject, body_text=None, body_html=None):
    """Send email via Postmark. Returns True on success."""
    postmark_key = config.get('POSTMARK_API_KEY')
    if not postmark_key:
        app.logger.warning('POSTMARK_API_KEY not set — email not sent to %s', to)
        app.logger.info('Email would be: subject=%s body=%s', subject, body_text or body_html)
        return True  # Pretend success in dev mode
    payload = {
        'From': config.get('EMAIL_FROM', 'Compunet Reborn <noreply@compunet.live>'),
        'To': to,
        'Subject': subject,
    }
    if body_html:
        payload['HtmlBody'] = body_html
    if body_text:
        payload['TextBody'] = body_text
    resp = requests.post(
        'https://api.postmarkapp.com/email',
        headers={
            'X-Postmark-Server-Token': postmark_key,
            'Content-Type': 'application/json',
        },
        json=payload,
    )
    if resp.status_code == 200:
        return True
    app.logger.error('Postmark error: %s %s', resp.status_code, resp.text)
    return False


def _server_path(*parts):
    """Resolve a path under the server tree, in either layout.

    ⚠ The two layouts genuinely differ, and hardcoding either one breaks the
    other:

      container — the Dockerfile puts app.py at /app and compose mounts the data
                  INSIDE it, at /app/server/data
      checkout  — app.py is at <repo>/website/, so the tree is one level UP

    Production ran for weeks on a hand-applied one-line patch to the partyline
    path because of this, re-applied by hand after every deploy (#117). This is
    the same try-then-fall-back approach the VERSION lookup at the top of this
    file already uses; it is here so the difference is handled once instead of
    at each call site.

    Returns the container path when neither exists, so a missing file behaves as
    "not there yet" rather than raising — the dev host has no such mount.
    """
    here = os.path.dirname(__file__)
    container = os.path.join(here, *parts)                 # /app/server/...
    checkout = os.path.join(here, '..', *parts)            # <repo>/server/...
    if os.path.exists(container):
        return container
    if os.path.exists(checkout):
        return checkout
    return container


def _client_ip():
    """The visitor's address, not the proxy in front of the site.

    ⚠ `request.remote_addr` is the TUNNEL here — the site is reached through
    Cloudflare, so the peer is a container address and recording it puts
    172.18.0.x against every event. CF-Connecting-IP holds exactly one address
    and only Cloudflare sets it; X-Forwarded-For is a chain the client can also
    append to, so only its first entry means anything.
    """
    cf = (request.headers.get('CF-Connecting-IP') or '').strip()
    if cf:
        return cf
    xff = request.headers.get('X-Forwarded-For') or ''
    first = xff.split(',')[0].strip()
    return first or request.remote_addr


def _audit_event(event, user=None, **details):
    """Record an event in the shared audit log, via the server that owns it.

    ⚠ This POSTs rather than writing the file, and that is deliberate. The
    website runs in its own container with `server/data` mounted READ-ONLY —
    it is the internet-facing half of the deployment and has no business
    writing to the content, mail or config trees. It already READS this log
    through the API (the admin audit page); writing goes the same way.

    It used to append to a path of its own, which under Docker resolved inside
    this container and vanished on the next recreate. Both events this function
    records — `password_reset_request` and `password_reset`, with user and IP —
    had therefore never once survived: 0 of the 6,566 entries in the live log.
    Precisely the trail you want when investigating a stolen account.

    Failure is logged, never raised: an audit write must not be able to break a
    password reset for the user in front of us.
    """
    try:
        resp = _api_post('/api/audit', {'event': event, 'user': user,
                                        'details': details})
        if resp.status_code != 200:
            app.logger.warning('Audit event %s rejected: %s %s',
                               event, resp.status_code, resp.text[:200])
    except requests.RequestException as e:
        app.logger.warning('Audit event %s not recorded: %s', event, e)


def _hash_password(password):
    return hashlib.sha256(password.upper().encode('utf-8')).hexdigest()


def _notify_admins_new_user(entry):
    """Send email to all admin users notifying them of a new registration."""
    resp = _api_get('/api/users')
    if resp.status_code != 200:
        return
    users = resp.json().get('users', [])
    admin_emails = [u['email'] for u in users if u.get('admin') and u.get('email')]
    date = time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())
    template_path = _server_path('server', 'cfg', 'new-user-notification.md')
    try:
        template = open(template_path).read()
    except OSError:
        template = 'New user: {{user_id}} ({{name}}, {{email}}) registered on {{date}}.'
    import markdown
    body_md = (template
               .replace('{{user_id}}', entry.get('user_id', ''))
               .replace('{{name}}', entry.get('name', ''))
               .replace('{{email}}', entry.get('email', ''))
               .replace('{{date}}', date))
    body_html = markdown.markdown(body_md)
    for email in admin_emails:
        _send_email(
            to=email,
            subject=f'Compunet Reborn — New user registered: {entry["user_id"]}',
            body_html=body_html,
        )


# ============================================================
# Public Pages
# ============================================================

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/connect')
def connect():
    return render_template('connect.html')


@app.route('/guide')
def guide():
    return render_template('guide.html')


@app.route('/extras')
def extras():
    return render_template('extras.html')


# ============================================================
# News (#35)
#
# Items are Markdown files in the repository, named `YYYY-MM-DD-slug.md`. The
# filename carries the date and the permalink; the first `# heading` is the
# title. No front-matter, no database.
#
# ⚠ Not published from the admin UI, deliberately. This container cannot write
# to the server tree (server/data is read-only, server/cfg is not mounted), so
# runtime publishing needs a server endpoint and a write path — real machinery
# for something published a handful of times a year. Files in git give version
# control, review and rollback instead, at the cost of a deploy per item.
#
# ⚠ markdown.markdown() passes RAW HTML THROUGH. That is acceptable only while
# the author is someone with commit access. If items ever become submittable at
# runtime, this needs sanitising first.
# ============================================================

NEWS_DIR = os.path.join(os.path.dirname(__file__), 'news')
_NEWS_NAME_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})-([a-z0-9-]+)\.md$')


def _news_items():
    """Every news item, newest first."""
    items = []
    if not os.path.isdir(NEWS_DIR):
        return items
    for name in os.listdir(NEWS_DIR):
        match = _NEWS_NAME_RE.match(name)
        if not match:
            continue
        date, slug = match.group(1), match.group(2)
        with open(os.path.join(NEWS_DIR, name), 'r', encoding='utf-8') as f:
            body = f.read()
        title, body = _split_news_title(body)
        items.append({'date': date, 'slug': slug, 'title': title, 'body': body,
                      'display_date': _news_display_date(date)})
    # Filename dates sort correctly as strings, and ties break on the slug so
    # the order is stable rather than filesystem-dependent.
    items.sort(key=lambda i: (i['date'], i['slug']), reverse=True)
    return items


def _news_display_date(date):
    """`2026-06-29` -> `29 June 2026`.

    Built from the parsed fields rather than a `%-d` format: that directive
    strips the leading zero on Linux but is not portable — on Windows it raises,
    which would take the page down on the developer's machine and nowhere else.
    Falls back to the raw value rather than failing a page over a misnamed file.
    """
    try:
        parsed = time.strptime(date, '%Y-%m-%d')
    except ValueError:
        return date
    return '%d %s %d' % (parsed.tm_mday, time.strftime('%B', parsed),
                         parsed.tm_year)


def _split_news_title(body):
    """Take the leading `# heading` as the title, and return the rest."""
    lines = body.strip().split('\n')
    if lines and lines[0].startswith('# '):
        return lines[0][2:].strip(), '\n'.join(lines[1:]).strip()
    return 'Untitled', body.strip()


def _render_news(body):
    import markdown as md
    return md.markdown(body, extensions=['extra'])


@app.route('/news')
def news():
    items = _news_items()
    for item in items:
        item['html'] = _render_news(item['body'])
    return render_template('news.html', items=items)


@app.route('/news/<slug>')
def news_item(slug):
    items = _news_items()
    for item in items:
        if item['slug'] == slug:
            item['html'] = _render_news(item['body'])
            # The full list too, for the index beside it.
            return render_template('news_item.html', item=item, items=items)
    # An item that has been renamed or withdrawn should land somewhere useful
    # rather than on an error page.
    flash('That news item no longer exists.', 'error')
    return redirect(url_for('news'))


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'GET':
        return render_template('contact.html')

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    message = request.form.get('message', '').strip()

    if not name or not email or not message:
        flash('Please fill in all fields.', 'error')
        return render_template('contact.html')

    _send_email(
        to='admin@compunet.live',
        subject=f'Compunet Reborn — Contact from {name}',
        body_text=f'From: {name} <{email}>\n\n{message}',
    )
    flash('Message sent! We\'ll get back to you soon.', 'success')
    return render_template('contact.html')


# ============================================================
# Registration
# ============================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    user_id = request.form.get('user_id', '').upper().strip()
    password = request.form.get('password', '').upper().strip()
    confirm_password = request.form.get('confirm_password', '').upper().strip()
    email = request.form.get('email', '').strip()
    name = request.form.get('name', '').strip()

    errors = []
    if not USERID_RE.match(user_id):
        errors.append('User ID must be 1-8 characters, A-Z and 0-9 only.')
    if not PASSWORD_RE.match(password):
        errors.append('Password must be 1-6 characters, A-Z and 0-9 only.')
    if password != confirm_password:
        errors.append('Passwords do not match.')
    if not email or '@' not in email:
        errors.append('A valid email address is required.')
    if not name:
        errors.append('Display name is required.')

    if not errors:
        resp = _api_get(f'/api/users/{user_id}')
        if resp.status_code == 200:
            errors.append('That User ID is already taken.')

    if errors:
        return render_template('register.html', errors=errors,
                               user_id=user_id, email=email, name=name)

    resp = _api_create_pending({
        'user_id': user_id,
        'password': password,
        'email': email,
        'name': name,
    })
    if resp.status_code != 201:
        errors.append('Registration failed. Please try again.')
        return render_template('register.html', errors=errors,
                               user_id=user_id, email=email, name=name)
    token = resp.json()['token']

    verify_url = f'{config.get("WEBSITE_BASE_URL", "http://localhost:6464")}/verify/{token}'
    _send_email(
        to=email,
        subject='Compunet Reborn — Verify Your Account',
        body_text=(
            f'Welcome to Compunet Reborn!\n\n'
            f'Your User ID: {user_id}\n\n'
            f'Please verify your email by visiting:\n{verify_url}\n\n'
            f'This link expires in 24 hours.\n\n'
            f'If you did not register, ignore this email.'
        ),
    )

    return render_template('register_success.html', email=email)


@app.route('/verify/<token>')
def verify(token):
    consume_resp = _api_consume_pending(token, outcome='approved')
    if consume_resp.status_code != 200:
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('register'))

    entry = consume_resp.json()
    if time.time() - entry.get('created', 0) > 86400:
        flash('Verification link has expired. Please register again.', 'error')
        return redirect(url_for('register'))

    resp = _api_post('/api/users', {
        'user_id': entry['user_id'],
        'password': entry['password'],
        'name': entry['name'],
        'email': entry.get('email', ''),
    })

    if resp.status_code == 201:
        _notify_admins_new_user(entry)
        return render_template('verify.html', user_id=entry['user_id'])
    elif resp.status_code == 409:
        flash('That User ID was taken while your verification was pending.', 'error')
        return redirect(url_for('register'))
    else:
        flash('Account creation failed. Please try again.', 'error')
        return redirect(url_for('register'))


# ============================================================
# Login / Session
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    user_id = request.form.get('user_id', '').upper().strip()
    password = request.form.get('password', '').upper().strip()

    # ⚠ Send the visitor's address. The server audits this sign-in but cannot
    # see who made it — its peer is this container — so an unsent address is
    # recorded as the website itself.
    resp = _api_post('/api/auth', {'user_id': user_id, 'password': password,
                                   'ip': _client_ip()})
    if resp.status_code != 200:
        flash('Invalid User ID or password.', 'error')
        return render_template('login.html', user_id=user_id)

    user_data = resp.json()
    session['user_id'] = user_data['user_id']
    session['name'] = user_data.get('name', '')
    flash('Login successful.', 'success')
    return redirect(url_for('account'))


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))


# ============================================================
# Account Management (authenticated)
# ============================================================

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    resp = _api_get(f'/api/users/{session["user_id"]}')
    if resp.status_code != 200:
        session.clear()
        return redirect(url_for('login'))
    return render_template('account.html', user=resp.json())


@app.route('/account/password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('password.html')

    new_password = request.form.get('new_password', '').upper().strip()
    confirm = request.form.get('confirm_password', '').upper().strip()

    if new_password != confirm:
        flash('Passwords do not match.', 'error')
        return render_template('password.html')
    if not PASSWORD_RE.match(new_password):
        flash('Password must be 1-6 characters, A-Z and 0-9 only.', 'error')
        return render_template('password.html')

    resp = _api_put(f'/api/users/{session["user_id"]}',
                    {'password': new_password, 'self_service': True})
    if resp.status_code == 200:
        flash('Password changed successfully.', 'success')
        return redirect(url_for('account'))
    else:
        flash('Failed to change password.', 'error')
        return render_template('password.html')


# ============================================================
# Directory header frames (#120)
#
# A directory's header is the PETSCII drawn above its entry list (§7.2 Part 1).
# The C64 ROM has no room for an upload command and the command vocabulary is
# closed, so this is the one place a user can set one.
#
# ⚠ Nothing is written here. This container mounts server/data READ-ONLY and
# has no access to server/cfg at all, so every change goes to the server over
# the admin API, which re-checks ownership itself.
# ============================================================

#: The server enforces this too — it is repeated here only so an oversized file
#: is refused before it is read into memory and base64'd.
MAX_HEADER_BYTES = 512

#: Longest entry title. The server enforces the same limit (compunet_server
#: MAX_TITLE); repeated here only so the form can stop over-typing at the source.
MAX_TITLE = 16


def _directories_for_session():
    """Directories the signed-in user may configure, or None on failure."""
    resp = _api_get(f'/api/directories?user={session["user_id"]}')
    if resp.status_code != 200:
        return None
    return resp.json().get('directories', [])


def _tree_for_session():
    """The whole hierarchy with this user's permissions resolved, or None."""
    resp = _api_get(f'/api/tree?user={session["user_id"]}')
    if resp.status_code != 200:
        return None
    return resp.json()


def _find_node(node, page_num):
    """Locate one entry in the tree.

    The tree arrives in a single response, so looking a page up in it costs
    nothing extra and avoids a second endpoint that could answer differently
    about the same page.
    """
    if node.get('page_num') == page_num:
        return node
    for child in node.get('children', []):
        found = _find_node(child, page_num)
        if found:
            return found
    return None


@app.route('/directories')
def directories():
    """The hierarchy. Everyone may browse it; editing is per-node."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    data = _tree_for_session()
    if data is None:
        flash('Could not reach the Compunet server.', 'error')
        return redirect(url_for('account'))
    # ⚠ Rows only. Frame panels and edit controls are fetched per entry when
    # someone asks for them (see the two fragment routes below). Rendering them
    # for every entry made the page grow with the tree: measured on a 30-page
    # fixture the controls alone were 61% of 183 KB, and the live tree has 269
    # pages.
    # ?edit=<n> is the no-script path for CHANGE: the server renders that one
    # entry's controls inline. With the script running, the same link is
    # intercepted and the fragment is fetched instead, so the tree never moves.
    edit_node = targets = None
    try:
        edit_num = int(request.args.get('edit', ''))
    except ValueError:
        edit_num = None
    if edit_num is not None:
        candidate = _find_node(data['tree'], edit_num)
        if candidate is not None and candidate.get('may_edit'):
            edit_node = candidate
            targets = _move_targets_for(data['tree'], edit_num)

    # ?header=<n> is the same idea for the HEADER control, and it is also where a
    # header POST comes back to — so a rejected upload reopens the panel it was
    # sent from instead of dropping the author on a bare tree (#126).
    header_node = None
    try:
        header_num = int(request.args.get('header', ''))
    except ValueError:
        header_num = None
    if header_num is not None:
        candidate = _find_node(data['tree'], header_num)
        if candidate is not None and candidate.get('may_configure'):
            header_node = candidate

    # ⚠ Drained here, deliberately, so base.html does not render them at the top of
    # the page. We arrive on this URL via #header-<n>, which scrolls the panel into
    # view — and scrolls a message at the top of a tall tree straight out of it. The
    # whole point of the upload notes is that the author reads them, so they belong
    # beside the panel they describe. get_flashed_messages consumes, so taking them
    # now is what stops them appearing twice.
    panel_messages = get_flashed_messages(with_categories=True) if header_node else None

    return render_template('tree.html', tree=data['tree'],
                           messages_in_page=bool(header_node),
                           duplicates=data.get('duplicate_page_numbers') or [],
                           edit_node=edit_node, node=edit_node or header_node,
                           header_node=header_node,
                           panel_messages=panel_messages,
                           max_bytes=MAX_HEADER_BYTES,
                           targets=targets, max_title=MAX_TITLE)


@app.route('/pages/<int:page_num>')
def view_page(page_num):
    """A text page's frames, as the C64 draws them."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    data = _tree_for_session()
    if data is None:
        flash('Could not reach the Compunet server.', 'error')
        return redirect(url_for('directories'))
    node = _find_node(data['tree'], page_num)
    if node is None:
        flash('No such page.', 'error')
        return redirect(url_for('directories'))
    if not node.get('viewable'):
        flash('%s holds nothing that can be shown here.' % node['title'], 'info')
        return redirect(url_for('directories'))
    return render_template('page_frames.html', node=node)


#: Fragment routes. Both return a piece of HTML rather than a page, so the tree
#: can fill in a panel without reloading. Server-rendered from the same macros the
#: page uses — there is no templating on the client, and no JSON to keep in step.
#:
#: ⚠ Each degrades to something that works with scripting off: VIEW is a real link
#: to /pages/<n>, and CHANGE is a real link to /directories?edit=<n>.

@app.route('/pages/<int:page_num>/panel')
def page_panel(page_num):
    """The frame viewer for one page."""
    if 'user_id' not in session:
        return '', 403
    data = _tree_for_session()
    node = _find_node(data['tree'], page_num) if data else None
    if node is None or not node.get('viewable'):
        return '', 404
    return render_template('_frame_panel.html', node=node)


@app.route('/directories/<int:page_num>/panel')
def directory_header_panel(page_num):
    """A directory's header frame and its owner-only setting, as a fragment."""
    if 'user_id' not in session:
        return '', 403
    data = _tree_for_session()
    node = _find_node(data['tree'], page_num) if data else None
    # may_configure, not may_edit: the root cannot be restructured but does own a
    # header frame, and gating this on may_edit hid that from the tree while the
    # settings page went on offering it.
    if node is None or not node.get('may_configure'):
        return '', 404
    return render_template('_header_panel.html', node=node,
                           max_bytes=MAX_HEADER_BYTES)


@app.route('/pages/<int:page_num>/controls')
def page_controls(page_num):
    """The rename / reorder / move / delete controls for one entry."""
    if 'user_id' not in session:
        return '', 403
    data = _tree_for_session()
    node = _find_node(data['tree'], page_num) if data else None
    if node is None or not node.get('may_edit'):
        return '', 404
    return render_template('_controls.html', node=node,
                           max_title=MAX_TITLE,
                           targets=_move_targets_for(data['tree'], page_num))


@app.route('/pages/<int:page_num>/frame/<int:index>.png')
def page_frame_png(page_num, index):
    """Proxy one rendered frame. See directory_header_png for why it is proxied."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    resp = _api_get('/api/pages/%d/frame/%d.png?user=%s'
                    % (page_num, index, session['user_id']))
    if resp.status_code != 200:
        return '', resp.status_code
    return Response(resp.content, mimetype='image/png',
                    headers={'Cache-Control': 'no-cache, must-revalidate'})


def _move_targets_for(tree, page_num):
    """Where ONE entry could be moved to: [{page_num, label}, ...].

    ⚠ Computed for a single node, on demand. The previous version built this for
    every node in the tree at once, which is O(n^2) — each of n entries carrying a
    select listing up to n destinations. On the live tree (269 pages) that was the
    single largest thing on the page. Now it is fetched when someone opens the
    controls for one entry.

    Excluded: itself and everything beneath it (a directory cannot be moved inside
    itself), the directory it is already in, any directory already holding its 11
    entries, and any the user may not add to. The server re-checks all of it —
    this only decides what to offer.
    """
    directories, parent_of, subtree = [], {}, {}

    def index(node, depth, parent_num):
        parent_of[node['page_num']] = parent_num
        if node.get('is_directory'):
            directories.append({
                'page_num': node['page_num'],
                # Non-breaking spaces: an <option> collapses ordinary runs, so
                # this is the only way to show depth in a plain select.
                'label': (' ' * (depth * 3)) + node['title'],
                'may_add': node.get('may_add'),
                'full': node.get('full'),
            })
        below = {node['page_num']}
        for child in node.get('children', []):
            below |= index(child, depth + 1, node['page_num'])
        subtree[node['page_num']] = below
        return below

    index(tree, 0, None)
    if page_num not in subtree:
        return []
    return [d for d in directories
            if d['may_add'] and not d['full']
            and d['page_num'] not in subtree[page_num]
            and d['page_num'] != parent_of[page_num]]


@app.route('/pages/<int:page_num>/move', methods=['POST'])
def move_page(page_num):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        dest = int(request.form.get('dest_page_num', ''))
    except ValueError:
        flash('Choose a directory to move it into.', 'error')
        return redirect(url_for('directories'))
    resp = _api_post('/api/pages/%d/move' % page_num,
                     {'user': session['user_id'], 'dest_page_num': dest})
    if resp.status_code == 200:
        body = resp.json()
        flash('Moved "%s" from %s to %s.'
              % (body.get('title'), body.get('was'), body.get('now')), 'success')
    else:
        flash(_api_error(resp, 'Could not move that entry.'), 'error')
    return redirect(url_for('directories'))


@app.route('/pages/<int:page_num>/delete', methods=['POST'])
def delete_page(page_num):
    """Delete an entry.

    ⚠ Two-step on purpose. A tree view is a list of near-identical rows and the
    realistic mistake is pressing the control on the wrong one, so the first press
    shows what would go and the second carries it out. The confirmation names the
    page number and title, and says the archive is not an undo button — which is
    true: nothing reads it back, so recovery means an operator restoring files by
    hand.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.form.get('confirm') != 'yes':
        data = _tree_for_session()
        node = _find_node(data['tree'], page_num) if data else None
        if node is None:
            flash('No such entry.', 'error')
            return redirect(url_for('directories'))
        return render_template('confirm_delete.html', node=node)

    resp = _api_delete_json('/api/pages/%d' % page_num,
                            {'user': session['user_id']})
    if resp.status_code == 200:
        body = resp.json()
        entries = body.get('entries', 1)
        flash('Deleted "%s"%s. %s archived — ask an admin if you need it back.'
              % (body.get('title'),
                 '' if entries == 1 else ' and the %d entries inside it' % (entries - 1),
                 'A copy was' if entries == 1 else 'Copies were'), 'success')
    else:
        flash(_api_error(resp, 'Could not delete that entry.'), 'error')
    return redirect(url_for('directories'))


@app.route('/pages/<int:page_num>/rename', methods=['POST'])
def rename_page(page_num):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    title = request.form.get('title', '')
    resp = _api_post('/api/pages/%d/rename' % page_num,
                     {'user': session['user_id'], 'title': title})
    if resp.status_code == 200:
        body = resp.json()
        flash('Renamed "%s" to "%s".' % (body.get('was'), body.get('title')),
              'success')
    else:
        flash(_api_error(resp, 'Could not rename that entry.'), 'error')
    return redirect(url_for('directories'))


@app.route('/pages/<int:page_num>/reorder', methods=['POST'])
def reorder_page(page_num):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        index = int(request.form.get('index', ''))
    except ValueError:
        flash('Choose a position.', 'error')
        return redirect(url_for('directories'))
    resp = _api_post('/api/pages/%d/reorder' % page_num,
                     {'user': session['user_id'], 'index': index})
    if resp.status_code == 200:
        flash('Moved to position %d in the listing.' % (index + 1), 'success')
    else:
        flash(_api_error(resp, 'Could not reorder that entry.'), 'error')
    return redirect(url_for('directories'))


@app.route('/directories/settings')
def directory_settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    dirs = _directories_for_session()
    if dirs is None:
        flash('Could not reach the Compunet server.', 'error')
        return redirect(url_for('account'))

    # ?header=<n> says which directory an upload just came back from, so its
    # results can be shown beside it. See the note in `directories` — this page is
    # a long list and we arrive anchored, so the top of it is already off screen.
    try:
        panel_page = int(request.args.get('header', ''))
    except ValueError:
        panel_page = None
    panel_messages = (get_flashed_messages(with_categories=True)
                      if panel_page is not None else None)

    return render_template('directories.html', directories=dirs,
                           messages_in_page=panel_page is not None,
                           panel_page=panel_page,
                           panel_messages=panel_messages,
                           max_bytes=MAX_HEADER_BYTES)


def _header_return(page_num=None):
    """Where a header form should send the user back to.

    ⚠ Only ever one of two known endpoints, never a URL from the request. Taking a
    redirect target from form input is how open-redirect bugs happen; the form only
    gets to say WHICH of our own pages it came from.

    `page_num` reopens the panel that was posted from. Without it the redirect
    landed on a bare page and the author lost their place — on the settings page
    that means scrolling a list of every directory they own to find the one whose
    upload just failed, which is most punishing for exactly the trivial mistakes
    (no file chosen) that are easiest to make.
    """
    tree = request.form.get('next') == 'tree'
    if page_num is None:
        return redirect(url_for('directories') if tree
                        else url_for('directory_settings'))
    if tree:
        # ?header=<n> re-renders the panel server-side, so this works with the
        # script running or not.
        return redirect(url_for('directories', header=page_num,
                                _anchor='panel-%d' % page_num))
    return redirect(url_for('directory_settings', header=page_num,
                            _anchor='panel-%d' % page_num))


@app.route('/directories/<int:page_num>/header', methods=['POST'])
def set_directory_header(page_num):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Remove is a separate button on the same form rather than a DELETE, because
    # a plain HTML form cannot issue one.
    if request.form.get('action') == 'remove':
        resp = _api_delete_json(f'/api/directories/{page_num}/header',
                                {'user': session['user_id']})
        if resp.status_code == 200:
            flash('Header removed. The directory uses the standard frame again.',
                  'success')
        else:
            flash(_api_error(resp, 'Could not remove the header.'), 'error')
        return _header_return(page_num)

    upload = request.files.get('header')
    if upload is None or not upload.filename:
        flash('Choose a .seq file to upload.', 'error')
        return _header_return(page_num)

    raw = upload.read(MAX_HEADER_BYTES + 1)
    if not raw:
        flash('That file is empty.', 'error')
        return _header_return(page_num)
    if len(raw) > MAX_HEADER_BYTES:
        flash('That file is larger than %d bytes, the most a header may be.'
              % MAX_HEADER_BYTES, 'error')
        return _header_return(page_num)

    resp = _api_post(f'/api/directories/{page_num}/header',
                     {'user': session['user_id'],
                      'data': base64.b64encode(raw).decode('ascii')})
    if resp.status_code == 200:
        payload = resp.json()
        described = payload.get('describe') or {}
        flash('Header set — %d bytes, %s. It appears the next time the '
              'directory is opened.'
              % (described.get('bytes', len(raw)),
                 _rows_phrase(described.get('rows_used'))), 'success')
        # Anything the server adjusted or wants to warn about (#126): the frame
        # header stripped off an editor save, a $92 appended, ink that will be
        # invisible against the directory background. Shown so an accepted upload
        # is never a silent edit — the author is told exactly what was changed.
        for note in payload.get('notes') or []:
            flash(note, 'warning' if note.startswith('Warning') else 'info')
        return _header_return(page_num)

    # A rejected frame comes back with one reason per problem, each naming the
    # byte offset. Showing them individually is the point of rejecting rather
    # than silently cleaning the file up.
    reasons = []
    try:
        reasons = resp.json().get('reasons') or []
    except ValueError:
        pass
    if reasons:
        for reason in reasons:
            flash(reason, 'error')
    else:
        flash(_api_error(resp, 'The server would not accept that header.'),
              'error')
    return _header_return(page_num)


@app.route('/directories/<int:page_num>/header.png')
def directory_header_png(page_num):
    """Proxy the server's rendition of this directory's header.

    ⚠ Proxied rather than linked directly: the image lives behind the admin API,
    which the browser must never be given the key for. The server still checks
    that the signed-in user owns the directory — this route passes who is asking
    and does not vouch for them.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    resp = _api_get('/api/directories/%d/header.png?user=%s'
                    % (page_num, session['user_id']))
    if resp.status_code != 200:
        # No header, or no font to draw it with. The template only asks for the
        # image when a header is set, so this is the racing case — someone
        # removed it in another tab.
        return '', 404
    return Response(resp.content, mimetype='image/png',
                    headers={'Cache-Control': 'no-cache, must-revalidate'})


@app.route('/directories/<int:page_num>/settings', methods=['POST'])
def set_directory_settings(page_num):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    owner_only = request.form.get('owner_only') == 'on'
    resp = _api_put(f'/api/directories/{page_num}/settings',
                    {'user': session['user_id'], 'owner_only': owner_only})
    if resp.status_code == 200:
        flash('Only you can add to this directory.' if owner_only
              else 'This directory follows the surrounding area again.',
              'success')
    else:
        flash(_api_error(resp, 'Could not change that setting.'), 'error')
    return _header_return(page_num)


@app.errorhandler(413)
def _too_large(_e):
    """Flask aborts oversized requests before any handler runs, so without this
    picking the wrong file — an image, say — answers with a bare 413 page."""
    flash('That file is far too large. A header frame is at most %d bytes.'
          % MAX_HEADER_BYTES, 'error')
    if 'user_id' in session:
        return _header_return(page_num)
    return redirect(url_for('login'))


def _rows_phrase(rows):
    """How much of the header region the artwork fills, counted the way a person
    would — the first row is row 1, not row 0 (#126). `rows` is a COUNT, so it
    needs no adjustment; the phrasing is what changes."""
    if not rows:
        return 'no rows used'
    return 'using row 1' if rows == 1 else 'using rows 1-%d' % rows


def _api_error(resp, fallback):
    try:
        return resp.json().get('error') or fallback
    except ValueError:
        return fallback


# ============================================================
# Admin Panel
# ============================================================

def _require_admin():
    """Check session user is the ADMIN account. Returns redirect or None."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['user_id'] != 'ADMIN':
        flash('Access denied.', 'error')
        return redirect(url_for('account'))
    return None


@app.route('/admin')
def admin_users():
    denied = _require_admin()
    if denied:
        return denied

    resp = _api_get('/api/users')
    users = resp.json().get('users', []) if resp.status_code == 200 else []

    resp_pending = _api_get('/api/pending')
    pending = resp_pending.json().get('pending', []) if resp_pending.status_code == 200 else []

    return render_template('admin_users.html', users=users, pending=pending)


@app.route('/admin/user/<user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    denied = _require_admin()
    if denied:
        return denied

    user_id = user_id.upper()

    if request.method == 'GET':
        resp = _api_get(f'/api/users/{user_id}')
        if resp.status_code != 200:
            flash('User not found.', 'error')
            return redirect(url_for('admin_users'))
        return render_template('admin_edit_user.html', user=resp.json())

    # POST — update user fields
    updates = {}
    new_password = request.form.get('password', '').upper().strip()
    if new_password:
        if not PASSWORD_RE.match(new_password):
            flash('Password must be 1-6 characters, A-Z and 0-9 only.', 'error')
            return redirect(url_for('admin_edit_user', user_id=user_id))
        updates['password'] = new_password

    name = request.form.get('name', '').strip()
    if name:
        updates['name'] = name

    email = request.form.get('email', '').strip()
    if email is not None:
        updates['email'] = email

    credit = request.form.get('credit', '').strip()
    if credit:
        try:
            updates['credit'] = float(credit)
        except ValueError:
            flash('Credit must be a number.', 'error')
            return redirect(url_for('admin_edit_user', user_id=user_id))

    account_type = request.form.get('account_type', '').upper().strip()
    if account_type:
        updates['account_type'] = account_type

    updates['editor'] = 'editor' in request.form

    if updates:
        resp = _api_put(f'/api/users/{user_id}', updates)
        if resp.status_code == 200:
            flash(f'User {user_id} updated.', 'success')
        else:
            flash(f'Update failed: {resp.json().get("error", "unknown")}', 'error')
    else:
        flash('No changes submitted.', 'info')

    return redirect(url_for('admin_edit_user', user_id=user_id))


@app.route('/admin/pending/<token>/approve', methods=['POST'])
def admin_approve_pending(token):
    denied = _require_admin()
    if denied:
        return denied

    consume_resp = _api_consume_pending(token, outcome='approved')
    if consume_resp.status_code != 200:
        flash('Pending registration not found or already consumed.', 'error')
        return redirect(url_for('admin_users'))

    entry = consume_resp.json()
    resp = _api_post('/api/users', {
        'user_id': entry['user_id'],
        'password': entry['password'],
        'name': entry['name'],
        'email': entry.get('email', ''),
    })

    if resp.status_code == 201:
        flash(f'User {entry["user_id"]} approved and created.', 'success')
    elif resp.status_code == 409:
        flash(f'User ID {entry["user_id"]} already exists.', 'error')
    else:
        flash('Failed to create user.', 'error')

    return redirect(url_for('admin_users'))


@app.route('/admin/pending/<token>/delete', methods=['POST'])
def admin_delete_pending(token):
    denied = _require_admin()
    if denied:
        return denied

    resp = _api_delete(f'/api/pending/{token}')
    if resp.status_code == 200:
        flash('Pending registration deleted.', 'success')
    else:
        flash('Failed to delete pending registration.', 'error')

    return redirect(url_for('admin_users'))


@app.route('/admin/broadcast', methods=['GET', 'POST'])
def admin_broadcast():
    denied = _require_admin()
    if denied:
        return denied

    if request.method == 'GET':
        return render_template('admin_broadcast.html')

    import markdown as md

    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    test_mode = request.form.get('test_mode', 'test') == 'test'

    if not subject or not body:
        flash('Subject and body are required.', 'error')
        return render_template('admin_broadcast.html', subject=subject, body=body)

    html_body = md.markdown(body)

    resp = _api_post('/api/broadcast', {
        'subject': subject,
        'body': html_body,
        'test_mode': test_mode,
    })

    if resp.status_code == 200:
        result = resp.json()
        mode = 'TEST' if result.get('test_mode') else 'ALL'
        flash(f'Broadcast sent ({mode}): {result.get("sent", 0)} delivered, {result.get("errors", 0)} errors.', 'success')
    else:
        flash(f'Broadcast failed: {resp.json().get("error", "unknown")}', 'error')

    return render_template('admin_broadcast.html', subject=subject, body=body)


@app.route('/admin/partyline')
def admin_partyline():
    denied = _require_admin()
    if denied:
        return denied

    api_key = config.get('COMPUNET_API_KEY')
    ws_url = config.get('PARTYLINE_WS_URL', '')
    if not ws_url:
        api_url = config.get('COMPUNET_API_URL', 'http://localhost:6403')
        ws_url = api_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/partyline'
    return render_template('admin_partyline.html', api_key=api_key, ws_url=ws_url,
                           user_id=session['user_id'])


@app.route('/admin/audit')
def admin_audit():
    denied = _require_admin()
    if denied:
        return denied

    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1
    try:
        per_page = min(500, max(10, int(request.args.get('per_page', 50))))
    except ValueError:
        per_page = 50

    # ⚠ Filtering happens SERVER-SIDE. Pulling the log here to filter it locally
    # would mean shipping the whole thing over the wire on every page view, and
    # it only grows (#128).
    filters = {k: request.args.get(k, '').strip()
               for k in ('user', 'event', 'kind', 'via', 'ip', 'from', 'to', 'q')}
    active = {k: v for k, v in filters.items() if v}

    query = urlencode({'page': page, 'per_page': per_page, **active})
    # An exact match count costs a full scan of the log, so ask for one only when
    # a filter is set — that is when the number is worth knowing. Unfiltered, the
    # pager is enough and the request stays cheap.
    if active:
        query += '&count=exact'
    resp = _api_get(f'/api/audit?{query}')
    data = resp.json() if resp.status_code == 200 else {}

    return render_template(
        'admin_audit.html',
        entries=data.get('entries', []),
        page=page, per_page=per_page,
        matched=data.get('matched', 0),
        matched_exact=data.get('matched_exact', False),
        has_more=data.get('has_more', False),
        all_events=data.get('events', []),
        all_kinds=data.get('kinds', []),
        filters=filters, active=active,
        # For building page links without losing the filters.
        base_query=urlencode(active))


@app.route('/admin/partyline-log')
def admin_partyline_log():
    denied = _require_admin()
    if denied:
        return denied

    page = int(request.args.get('page', 1))
    per_page = 50

    # Read partyline log directly (it's on the same filesystem in Docker)
    log_path = _server_path('server', 'data', 'partyline.jsonl')
    entries = []
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    # Reverse for newest first
    entries.reverse()
    total = len(entries)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    start = (page - 1) * per_page
    entries = entries[start:start + per_page]

    return render_template('admin_partyline_log.html', entries=entries,
                           page=page, total_pages=total_pages)


# ============================================================
# Password Reset
# ============================================================

RESETS_FILE = _server_path('server', 'cfg', 'password-resets.json')


def _load_resets():
    if os.path.exists(RESETS_FILE):
        with open(RESETS_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_resets(resets):
    os.makedirs(os.path.dirname(RESETS_FILE), exist_ok=True)
    with open(RESETS_FILE, 'w') as f:
        json.dump(resets, f, indent=2)


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')

    email = request.form.get('email', '').strip()
    if not email:
        flash('Please enter your email address.', 'error')
        return render_template('forgot_password.html')

    # Always show the same message (don't reveal if account exists)
    flash('If an account with that email exists, a reset link has been sent.', 'info')

    # Look up user by email
    resp = _api_get('/api/users')
    if resp.status_code == 200:
        users = resp.json().get('users', [])
        matching = [u for u in users if u.get('email', '').lower() == email.lower()]
        if matching:
            user = matching[0]
            user_id = user['user_id']
            token = hashlib.sha256(
                f'{user_id}{time.time()}{os.urandom(16).hex()}'.encode()
            ).hexdigest()[:32]
            resets = _load_resets()
            resets[token] = {
                'user_id': user_id,
                'created': time.time(),
            }
            _save_resets(resets)

            reset_url = f'{config.get("WEBSITE_BASE_URL", "http://localhost:6464")}/reset-password/{token}'
            template_path = _server_path('server', 'cfg', 'password-reset.md')
            try:
                template = open(template_path).read()
            except OSError:
                template = 'Reset your password: {{reset_url}}'
            import markdown
            body_md = (template
                       .replace('{{name}}', user.get('name', user_id))
                       .replace('{{user_id}}', user_id)
                       .replace('{{reset_url}}', reset_url))
            body_html = markdown.markdown(body_md)
            _send_email(
                to=email,
                subject='Compunet Reborn — Password Reset',
                body_html=body_html,
            )
            _audit_event('password_reset_requested', user=user_id, ip=_client_ip())

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    resets = _load_resets()
    entry = resets.get(token)

    if not entry:
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('forgot_password'))

    if time.time() - entry.get('created', 0) > 86400:
        del resets[token]
        _save_resets(resets)
        flash('Reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'GET':
        return render_template('reset_password.html', token=token, user_id=entry['user_id'])

    password = request.form.get('password', '').upper().strip()
    confirm = request.form.get('confirm_password', '').upper().strip()

    if not PASSWORD_RE.match(password):
        flash('Password must be 1-6 characters, A-Z and 0-9 only.', 'error')
        return render_template('reset_password.html', token=token, user_id=entry['user_id'])
    if password != confirm:
        flash('Passwords do not match.', 'error')
        return render_template('reset_password.html', token=token, user_id=entry['user_id'])

    resp = _api_put(f'/api/users/{entry["user_id"]}', {'password': password})
    if resp.status_code == 200:
        del resets[token]
        _save_resets(resets)
        _audit_event('password_reset', user=entry['user_id'], ip=_client_ip())
        flash('Password reset successfully. You can now log in.', 'success')
        return redirect(url_for('login'))
    else:
        flash('Password reset failed. Please try again.', 'error')
        return render_template('reset_password.html', token=token, user_id=entry['user_id'])


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6464, debug=True)
