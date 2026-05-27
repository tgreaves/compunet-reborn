"""Compunet Reborn — Website (Registration + Account Management)"""

import hashlib
import json
import os
import re
import time

import requests
from flask import (Flask, flash, redirect, render_template, request,
                   session, url_for)

import config

app = Flask(__name__)
app.secret_key = config.get('WEBSITE_SECRET_KEY', 'dev-secret-change-me')

_version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
if not os.path.exists(_version_file):
    _version_file = os.path.join(os.path.dirname(__file__), '..', 'VERSION')
APP_VERSION = open(_version_file).read().strip() if os.path.exists(_version_file) else 'unknown'


@app.context_processor
def inject_version():
    return {'version': APP_VERSION}

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


def _api_create_pending(data):
    return requests.post(
        f'{config.get("COMPUNET_API_URL", "http://localhost:6403")}/api/pending',
        headers=_api_headers(), json=data)


def _api_consume_pending(token):
    return requests.delete(
        f'{config.get("COMPUNET_API_URL", "http://localhost:6403")}/api/pending/{token}',
        headers=_api_headers())


def _send_email(to, subject, body_text=None, body_html=None):
    """Send email via Postmark. Returns True on success."""
    postmark_key = config.get('POSTMARK_API_KEY')
    if not postmark_key:
        app.logger.warning('POSTMARK_API_KEY not set — email not sent to %s', to)
        app.logger.info('Email would be: subject=%s body=%s', subject, body_text or body_html)
        return True  # Pretend success in dev mode
    payload = {
        'From': config.get('EMAIL_FROM', 'noreply@compunet.live'),
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


AUDIT_LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'server', 'data', 'audit.jsonl')

def _audit_event(event, user=None, **details):
    """Append an event to the shared audit log."""
    import datetime
    entry = {
        'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'event': event,
    }
    if user:
        entry['user'] = user
    entry.update(details)
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except OSError:
        app.logger.warning('Failed to write audit log entry: %s', entry)


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
    template_path = os.path.join(os.path.dirname(__file__), '..', 'server', 'cfg', 'new-user-notification.md')
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
    consume_resp = _api_consume_pending(token)
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

    resp = _api_post('/api/auth', {'user_id': user_id, 'password': password})
    if resp.status_code != 200:
        flash('Invalid User ID or password.', 'error')
        return render_template('login.html', user_id=user_id)

    user_data = resp.json()
    session['user_id'] = user_data['user_id']
    session['name'] = user_data.get('name', '')
    flash('Login successful.', 'success')
    return redirect(url_for('account'))


@app.route('/logout')
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

    resp = _api_put(f'/api/users/{session["user_id"]}', {'password': new_password})
    if resp.status_code == 200:
        flash('Password changed successfully.', 'success')
        return redirect(url_for('account'))
    else:
        flash('Failed to change password.', 'error')
        return render_template('password.html')


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


@app.route('/admin/pending/<token>/approve')
def admin_approve_pending(token):
    denied = _require_admin()
    if denied:
        return denied

    consume_resp = _api_consume_pending(token)
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


@app.route('/admin/pending/<token>/delete')
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

    page = int(request.args.get('page', 1))
    per_page = 50
    resp = _api_get(f'/api/audit?page={page}&per_page={per_page}')
    data = resp.json() if resp.status_code == 200 else {}
    entries = data.get('entries', [])
    total = data.get('total', 0)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    return render_template('admin_audit.html', entries=entries,
                           page=page, total_pages=total_pages)


# ============================================================
# Password Reset
# ============================================================

RESETS_FILE = os.path.join(os.path.dirname(__file__), '..', 'server', 'cfg', 'password-resets.json')


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
            template_path = os.path.join(os.path.dirname(__file__), '..', 'server', 'cfg', 'password-reset.md')
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
            _audit_event('password_reset_request', user=user_id, ip=request.remote_addr)

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
        _audit_event('password_reset', user=entry['user_id'], ip=request.remote_addr)
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
