from flask_login import UserMixin, current_user
from app.db import execute_query
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import abort

class User(UserMixin):
    def __init__(self, id, username, email, password_hash, role):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role

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
                role=user_data['role']
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
                role=user_data['role']
            )
        return None

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator