from flask_login import UserMixin, current_user
from app.db import execute_query
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import abort
from datetime import datetime, timedelta
import re

class User(UserMixin):
    def __init__(self, id, username, email, password_hash, role, failed_login_attempts=0, is_locked=False, locked_until=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.failed_login_attempts = failed_login_attempts
        self.is_locked = is_locked
        self.locked_until = locked_until

    @staticmethod
    def validate_input(username, email, password=None):
        """Validate user input to prevent injection and ensure quality."""
        errors = []
        
        # Validate username
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if len(username) > 50:
            errors.append("Username must not exceed 50 characters.")
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            errors.append("Username can only contain letters, numbers, dots, underscores, and hyphens.")
        
        # Validate email
        if not email or len(email) > 100:
            errors.append("Email must be valid and not exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors.append("Email format is invalid.")
        
        # Validate password (if provided)
        if password is not None:
            if len(password) < 6:
                errors.append("Password must be at least 6 characters.")
            if len(password) > 128:
                errors.append("Password must not exceed 128 characters.")
        
        return errors

    @staticmethod
    def create(username, email, password, role='STORE_PERSON'):
        hashed_password = generate_password_hash(password)
        query = """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, %s) RETURNING id;
        """
        result = execute_query(query, (username, email, hashed_password, role), fetchone=True, commit=True)
        return result['id'] if result else None

    @staticmethod
    def get_by_username_or_email(identifier):
        query = "SELECT * FROM users WHERE username = %s OR email = %s;"
        user_data = execute_query(query, (identifier, identifier), fetchone=True)
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data['role'],
                failed_login_attempts=user_data.get('failed_login_attempts', 0),
                is_locked=user_data.get('is_locked', False),
                locked_until=user_data.get('locked_until')
            )
        return None

    @staticmethod
    def get_by_id(user_id):
        query = "SELECT * FROM users WHERE id = %s;"
        user_data = execute_query(query, (user_id,), fetchone=True)
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data['role'],
                failed_login_attempts=user_data.get('failed_login_attempts', 0),
                is_locked=user_data.get('is_locked', False),
                locked_until=user_data.get('locked_until')
            )
        return None

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def is_account_locked(user):
        """Check if account is locked and if lockout period has expired."""
        if not user.is_locked:
            return False
        
        if user.locked_until and datetime.now() > user.locked_until:
            # Lockout period expired, unlock the account
            execute_query(
                "UPDATE users SET is_locked = FALSE, locked_until = NULL, failed_login_attempts = 0 WHERE id = %s;",
                (user.id,),
                commit=True
            )
            return False
        
        return True

    @staticmethod
    def record_failed_login(user_id):
        """Increment failed login attempts and lock if threshold exceeded."""
        user_data = execute_query(
            "SELECT failed_login_attempts FROM users WHERE id = %s;",
            (user_id,),
            fetchone=True
        )
        
        if not user_data:
            return
        
        failed_attempts = user_data['failed_login_attempts'] + 1
        
        # Lock account after 5 failed attempts
        if failed_attempts >= 5:
            locked_until = datetime.now() + timedelta(minutes=30)
            execute_query(
                "UPDATE users SET failed_login_attempts = %s, is_locked = TRUE, locked_until = %s WHERE id = %s;",
                (failed_attempts, locked_until, user_id),
                commit=True
            )
        else:
            execute_query(
                "UPDATE users SET failed_login_attempts = %s WHERE id = %s;",
                (failed_attempts, user_id),
                commit=True
            )

    @staticmethod
    def clear_failed_login(user_id):
        """Clear failed login attempts on successful login."""
        execute_query(
            "UPDATE users SET failed_login_attempts = 0 WHERE id = %s;",
            (user_id,),
            commit=True
        )
    
  # adding two methods for manage users for admin panel
    @staticmethod
    def get_all_users():
        """Get all non-admin users (for admin panel)."""
        query = "SELECT id, username, email, role FROM users WHERE role = 'STORE_PERSON' ORDER BY username;"
        return execute_query(query, fetchall=True)

    @staticmethod
    def update_password(user_id, new_password):
        """Update user password and unlock account."""
        hashed_password = generate_password_hash(new_password)
        execute_query(
            "UPDATE users SET password_hash = %s, failed_login_attempts = 0, is_locked = FALSE, locked_until = NULL WHERE id = %s;",
            (hashed_password, user_id),
            commit=True
        )

    @staticmethod
    def is_recovery_code_valid(code):
        """Validate recovery code against environment variable."""
        from app.config import Config
        return code == Config.ADMIN_RECOVERY_CODE and Config.ADMIN_RECOVERY_CODE != ''  


def role_required(*roles):
    """Decorator to restrict access to specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
