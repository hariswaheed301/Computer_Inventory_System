import logging
import sys
from flask import Flask, session, request, jsonify, render_template, redirect, flash, url_for
from psycopg2 import OperationalError
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException

from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.config import Config
from app.models.users import User


login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address
)

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config.get('APP_ENV') == 'production':
        secret_key = app.config.get('SECRET_KEY')
        if not secret_key or secret_key == 'default-dev-key':
            raise RuntimeError('SECRET_KEY must be set to a strong value in production.')

        # Ensure Flask does not leak debug tracebacks in production responses.
        app.config['PROPAGATE_EXCEPTIONS'] = False
        app.config['TRAP_HTTP_EXCEPTIONS'] = False
        app.config['TRAP_BAD_REQUEST_ERRORS'] = False

    # Respect Render/reverse proxy headers for scheme and client IP.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Configure logging
    log_level = logging.DEBUG if app.config.get('APP_ENV') == 'development' else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log') if app.config.get('APP_ENV') == 'production' else logging.NullHandler()
        ]
    )
    app.logger.setLevel(log_level)
    app.logger.info(f"Application starting in {app.config.get('APP_ENV')} mode")

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    
    csrf.init_app(app)
    limiter.init_app(app)



    # Add Security Headers Middleware
    @app.before_request
    def manage_session():

        session.permanent = True



    @app.after_request
    def set_security_headers(response):
        # Fix MIME type for .js files (Flask sometimes serves as text/plain on Windows)
        if response.content_type and 'text/plain' in response.content_type:
            path = request.path if hasattr(request, 'path') else ''
            if path.endswith('.js'):
                response.content_type = 'application/javascript; charset=utf-8'
        
        # Force HTTPS in production
        if app.config.get('APP_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # XSS Protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Reduce MIME sniffing risks
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Restrict powerful browser features by default
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self';"
)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        
        return response

    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f"404 Not Found: {request.path}")
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f"403 Forbidden: {request.path} by {request.remote_addr}")
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):

        app.logger.exception(
            f"500 Internal Error: {request.path}"
        )

        return render_template("errors/500.html"), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        # Let explicit HTTP handlers (404/403/429 etc.) continue to work.
        if isinstance(error, HTTPException):
            return error

        app.logger.exception(f"Unhandled exception on {request.path}")

        if app.config.get('APP_ENV') == 'production':
            return render_template('errors/500.html'), 500

        # In development, re-raise so local debugging remains easy.
        raise error


    @app.errorhandler(429)
    def ratelimit_error(error):
        app.logger.warning(f"429 Rate Limited: {request.remote_addr} on {request.path}")
        flash('Too many requests. Please slow down.', 'warning')
        return redirect(url_for('auth.login'))

    # Register Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.stock_routes import stock_bp
    from app.routes.store_routes import store_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(store_bp)
    
    # Apply rate limiting to login endpoint
    limiter.limit("5 per 15 minutes")(app.view_functions['auth.login'])
    limiter.limit("5 per 15 minutes")(app.view_functions['auth.forgot_password'])
    limiter.limit("5 per 15 minutes")(app.view_functions['auth.verify_recovery_code'])
    limiter.limit("5 per 15 minutes")(app.view_functions['auth.reset_password'])
    limiter.limit("20 per hour")(app.view_functions['store.confirm_order'])

    return app
