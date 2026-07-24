from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.models.users import User, role_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'STORE_PERSON')

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
        identifier = request.form.get('identifier').strip()
        password = request.form.get('password')

        user = User.get_by_username_or_email(identifier)

        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('stock.dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
