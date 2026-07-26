from flask import Flask, session
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.config import Config
from app.models.users import User
from datetime import timedelta

login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    
    csrf.init_app(app)
    limiter.init_app(app)

    # Add Security Headers Middleware
    @app.before_request
    def make_session_permanent():
        """Ensure session is marked permanent for timeout handling."""
        session.permanent = True
        app.permanent_session_lifetime = timedelta(minutes=15)
        session.modified = True

    @app.after_request
    def set_security_headers(response):
        # Force HTTPS in production
        if app.config.get('APP_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy (allow only same-origin + CDN resources)
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' cdn.jsdelivr.net use.fontawesome.com; "
            "style-src 'self' cdn.jsdelivr.net; "
            "font-src 'self' cdnjs.cloudflare.com use.fontawesome.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
        
        return response

    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.stock_routes import stock_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(stock_bp)
    
    # Apply rate limiting to login endpoint
    limiter.limit("5 per 15 minutes")(app.view_functions['auth.login'])

    return app