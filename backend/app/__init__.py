# app/__init__.py
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_cors import CORS
from config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()  # 追加

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    print("=== Application Configuration ===")
    print(f"MAILGUN_API_KEY: {'*' * 8 if app.config.get('MAILGUN_API_KEY') else 'Not Set'}")
    print(f"MAILGUN_DOMAIN: {app.config.get('MAILGUN_DOMAIN') or 'Not Set'}")
    print(f"ADMIN_EMAIL: {app.config.get('ADMIN_EMAIL') or 'Not Set'}")
    print("==============================")
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)

    # メール設定の初期化
    mail.init_app(app)
    
    # Register blueprints
    from app.api.auth import bp as auth_bp
    from app.api.designs import bp as designs_bp
    from app.api.cart import bp as cart_bp
    from app.api.payment import bp as payment_bp
    from app.api.orders import bp as orders_bp
    from app.api.admin import bp as admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(designs_bp, url_prefix='/api/designs')
    app.register_blueprint(cart_bp, url_prefix='/api/cart')
    app.register_blueprint(payment_bp, url_prefix='/api/payment')
    app.register_blueprint(orders_bp, url_prefix='/api/orders')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({'error': 'Bad request'}), 400
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        return jsonify({'error': 'Unauthorized access'}), 401
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({'error': 'Forbidden'}), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    return app