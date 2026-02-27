"""Flask application factory."""
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import config_by_name
from app.extensions import (
    db,
    migrate,
    limiter,
    init_qdrant,
    init_neo4j,
    init_elasticsearch,
    init_redis,
    close_extensions
)
from app.middleware.auth import jwt_required
from firebase_config import initialize_firebase
import structlog

logger = structlog.get_logger()


def create_app(config_name='default'):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:3001"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Authorization", "Content-Type"]
        }
    })

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # 🔥 Initialize Firebase Admin SDK
    try:
        initialize_firebase()
        logger.info("Firebase initialized successfully")
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")

    with app.app_context():
        # Initialize external databases
        try:
            init_qdrant(app)
            logger.info("Qdrant initialized")
        except Exception as e:
            logger.warning(f"Qdrant initialization failed: {e}")

        try:
            init_neo4j(app)
            logger.info("Neo4j initialized")
        except Exception as e:
            logger.warning(f"Neo4j initialization failed: {e}")

        try:
            init_elasticsearch(app)
            logger.info("Elasticsearch initialized")
        except Exception as e:
            logger.warning(f"Elasticsearch initialization failed: {e}")

        try:
            init_redis(app)
            logger.info("Redis initialized")
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Register teardown
    app.teardown_appcontext(lambda exc: close_extensions())

    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'career-intelligence-api'
        })

    # Protected test endpoint
    @app.route('/api/protected')
    @jwt_required
    def protected():
        return jsonify({'message': 'This is a protected endpoint'})

    logger.info("Application initialized", config=config_name)
    return app


def register_blueprints(app):
    """Register Flask blueprints."""
    from app.routes.auth import auth_bp
    from app.routes.resume import resume_bp
    from app.routes.job import job_bp
    from app.routes.recommendation import recommendation_bp
    from app.routes.scraping import scraping_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(resume_bp, url_prefix='/api/resume')
    app.register_blueprint(job_bp, url_prefix='/api/jobs')
    app.register_blueprint(recommendation_bp, url_prefix='/api/recommendations')
    app.register_blueprint(scraping_bp, url_prefix='/api/scraping')


def register_error_handlers(app):
    """Register error handlers."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request', 'message': str(error.description)}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found', 'message': 'Resource not found'}), 404

    @app.errorhandler(429)
    def rate_limit(error):
        return jsonify({'error': 'Rate limit exceeded', 'message': 'Too many requests'}), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error', 'message': 'Something went wrong'}), 500