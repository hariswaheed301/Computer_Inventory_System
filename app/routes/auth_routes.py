from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.models.users import User, role_required
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'STORE_PERSON')

        # Input validation
        validation_errors = User.validate_input(username, email, password)
        if validation_errors:
            for error in validation_errors:
                flash(error, 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('auth/register.html')

        if User.get_by_username_or_email(username) or User.get_by_username_or_email(email):
            flash('Username or Email is already taken.', 'danger')
            return render_template('auth/register.html')

        User.create(username, email, password, role)
        flash('Staff account created successfully.', 'success')
        return redirect(url_for('auth.register'))

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        # Input validation
        if not identifier or not password:
            flash('Username/Email and password are required.', 'danger')
            return render_template('auth/login.html')

        if len(identifier) > 100 or len(password) > 128:
            flash('Invalid input detected.', 'danger')
            return render_template('auth/login.html')

        user = User.get_by_username_or_email(identifier)

        # Check if account is locked
        if user and User.is_account_locked(user):
            remaining_time = (user.locked_until - datetime.now()).seconds // 60
            flash(f'Account locked. Try again in {remaining_time} minutes.', 'danger')
            return render_template('auth/login.html')

        if user and user.check_password(password):
            # Clear failed attempts on successful login
            User.clear_failed_login(user.id)
            
            # Set permanent session for timeout handling
            login_user(user)
            session = __import__('flask').session
            session.permanent = True
            
            flash('Logged in successfully!', 'success')
            return redirect(url_for('stock.dashboard'))
        else:
            # Record failed login attempt
            if user:
                User.record_failed_login(user.id)
                # Check if just locked
                updated_user = User.get_by_id(user.id)
                if User.is_account_locked(updated_user):
                    flash('Account locked due to multiple failed attempts. Try again in 30 minutes.', 'danger')
                else:
                    attempts_left = 5 - updated_user.failed_login_attempts
                    flash(f'Invalid credentials. {attempts_left} attempts remaining before lockout.', 'danger')
            else:
                flash('Invalid username/email or password.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
