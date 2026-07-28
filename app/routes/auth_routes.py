from flask import Blueprint, render_template, redirect, url_for, flash, request, session, make_response, current_app
from flask_login import login_user, logout_user, login_required
from app.models.users import User, role_required
from datetime import datetime
from app.config import Config
from psycopg2 import OperationalError


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

        try:
            user = User.get_by_username_or_email(identifier)

        except OperationalError:

            current_app.logger.exception("Database unavailable during login.")

            flash(
                "Database temporarily unavailable. Please try again.",
                "danger"
            )

            return render_template("auth/login.html")


        # Check if account is locked
        if user and User.is_account_locked(user):
            remaining_time = (user.locked_until - datetime.now()).seconds // 60
            flash(f'Account locked. Try again in {remaining_time} minutes.', 'danger')
            return render_template('auth/login.html')

        if user and user.check_password(password):
            # Clear failed attempts on successful login
            User.clear_failed_login(user.id)
            
            # # Set permanent session for timeout handling
            # login_user(user)
           # Clear old session data
            session.clear()

            # Login user
            login_user(user)

            # Enable timeout
            session.permanent = True
            session.modified = True
            
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

    session.clear()

    response = make_response(
        redirect(url_for('auth.login'))
    )

    response.delete_cookie(
        current_app.config['SESSION_COOKIE_NAME'],
        path='/'
    )

    flash('Logged out successfully.', 'info')

    return response







@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():

    show_form = True
    store_message = None

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()

        if not identifier:
            flash('Please enter username or email.', 'danger')
            return render_template(
                'auth/forgot_password.html',
                show_form=True
            )

        user = User.get_by_username_or_email(identifier)

        if not user:
            # Do not reveal whether user exists
            flash(
                'If an account exists, a recovery message will be shown.',
                'info'
            )
            return render_template(
                'auth/forgot_password.html',
                show_form=True
            )

        # Store person cannot reset password
        if user.role == 'STORE_PERSON':

            show_form = False

            store_message = (
                "Your account is managed by your administrator. "
                f"Please contact: {Config.ADMIN_CONTACT_EMAIL}"

            )

            return render_template(
                'auth/forgot_password.html',
                show_form=show_form,
                store_message=store_message
            )


        # Admin recovery
        if user.role == 'ADMIN':
            session['recovery_user_id'] = user.id
            return redirect(
                url_for('auth.verify_recovery_code')
            )


    return render_template(
        'auth/forgot_password.html',
        show_form=True
    )


@auth_bp.route('/verify-recovery-code', methods=['GET', 'POST'])
def verify_recovery_code():
    recovery_user_id = session.get('recovery_user_id')
    
    if not recovery_user_id:
        flash('Invalid recovery session. Please try again.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        code = request.form.get('recovery_code', '').strip()
        
        if User.is_recovery_code_valid(code):
            session['recovery_verified'] = True
            session['recovery_user_id'] = recovery_user_id
            return redirect(url_for('auth.reset_password'))
        else:
            flash('Invalid recovery code. Please try again.', 'danger')
    
    return render_template('auth/verify_recovery_code.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('recovery_verified'):
        flash('Recovery verification required. Please start over.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    recovery_user_id = session.get('recovery_user_id')
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not new_password or not confirm_password:
            flash('Password fields are required.', 'danger')
            return render_template('auth/reset_password.html')
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html')
        
        validation_errors = User.validate_input('temp', 'temp@temp.com', new_password)
        if validation_errors:
            for error in validation_errors:
                flash(error, 'danger')
            return render_template('auth/reset_password.html')
        
        # Update password
        User.update_password(recovery_user_id, new_password)
        
        # Clear session
        session.pop('recovery_verified', None)
        session.pop('recovery_user_id', None)
        
        flash('Password reset successfully! Please login with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html')

@auth_bp.route('/manage-users')
@login_required
@role_required('ADMIN')
def manage_users():
    """Admin page to view and manage all users."""
    users = User.get_all_users()
    return render_template('auth/manage_users.html', users=users)


@auth_bp.route('/admin/reset-user-password/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def admin_reset_user_password(user_id):
    # Get the user to reset
    user_to_reset = User.get_by_id(user_id)
    
    if not user_to_reset or user_to_reset.role == 'ADMIN':
        flash('Invalid user or cannot reset admin password.', 'danger')
        return redirect(url_for('stock.dashboard'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not new_password or not confirm_password:
            flash('Password fields are required.', 'danger')
            return render_template('auth/admin_reset_user_password.html', user=user_to_reset)
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/admin_reset_user_password.html', user=user_to_reset)
        
        validation_errors = User.validate_input('temp', 'temp@temp.com', new_password)
        if validation_errors:
            for error in validation_errors:
                flash(error, 'danger')
            return render_template('auth/admin_reset_user_password.html', user=user_to_reset)
        
        # Update password
        User.update_password(user_id, new_password)
        
        flash(f'Password for {user_to_reset.username} has been reset successfully.', 'success')
        return redirect(url_for('stock.dashboard'))
    
    return render_template('auth/admin_reset_user_password.html', user=user_to_reset)
