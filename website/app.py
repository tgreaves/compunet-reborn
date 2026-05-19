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


def _send_email(to, subject, body_text):
    """Send email via Postmark. Returns True on success."""
    postmark_key = config.get('POSTMARK_API_KEY')
    if not postmark_key:
        app.logger.warning('POSTMARK_API_KEY not set — email not sent to %s', to)
        app.logger.info('Email would be: subject=%s body=%s', subject, body_text)
        return True  # Pretend success in dev mode
    resp = requests.post(
        'https://api.postmarkapp.com/email',
        headers={
            'X-Postmark-Server-Token': postmark_key,
            'Content-Type': 'application/json',
        },
        json={
            'From': config.get('EMAIL_FROM', 'noreply@compunet.live'),
            'To': to,
            'Subject': subject,
            'TextBody': body_text,
        },
    )
    if resp.status_code == 200:
        return True
    app.logger.error('Postmark error: %s %s', resp.status_code, resp.text)
    return False


def _hash_password(password):
    return hashlib.sha256(password.upper().encode('utf-8')).hexdigest()


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


# ============================================================
# Password Reset
# ============================================================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')

    email = request.form.get('email', '').strip()
    # Look up user by email — we need email stored in users.json for this.
    # For now: show generic "if account exists" message regardless.
    # TODO: Add email field to users.json and /api/users lookup by email
    flash('If an account with that email exists, a reset link has been sent.', 'info')
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # TODO: Implement with token-based reset flow
    flash('Password reset is not yet implemented.', 'info')
    return redirect(url_for('login'))


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6464, debug=True)
