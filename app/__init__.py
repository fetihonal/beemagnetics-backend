from flask import Flask, request, jsonify
from app.extensions import db, jwt
from app.config import DevelopmentConfig
from app.auth import auth_bp
from app.components import components_bp
from flask_migrate import Migrate
from flask_cors import CORS # type: ignore
import os

# Use Python-based LLC simulation (no MATLAB) by default
# Set USE_MATLAB=1 environment variable to use old MATLAB version
USE_MATLAB = os.environ.get('USE_MATLAB', '0') == '1'

if USE_MATLAB:
    print("⚠️  Using MATLAB-based LLC simulation (SLOW)")
    from app.LLC.llc import llc_bp
    from app.main import main  # Old MATLAB-based main blueprint
    from app.main import main as pfc_bp  # Old MATLAB-based PFC
else:
    print("✅ Using Python-based LLC simulation (FAST - No MATLAB)")
    from app.LLC.llc_v2 import llc_bp_v2 as llc_bp
    from app.PFC.pfc_v2 import pfc_bp_v2 as pfc_bp  # Python-based PFC
    # Create a dummy main blueprint for non-MATLAB mode
    from flask import Blueprint
    main = Blueprint('main', __name__)

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(DevelopmentConfig)

    # Initialize db, jwt, and migrate
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Global CORS configuration
    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

    @app.before_request
    def handle_options():
        if request.method == 'OPTIONS':
            return '', 204

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main)
    app.register_blueprint(llc_bp)
    app.register_blueprint(pfc_bp)  # PFC Blueprint added
    app.register_blueprint(components_bp)  # Component Database API

    app.config["JWT_BLACKLIST_ENABLED"] = True
    app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access", "refresh"]

    # Log simulation mode
    mode = "MATLAB" if USE_MATLAB else "Python (No MATLAB)"
    print(f"🚀 LLC Simulation Mode: {mode}")
    print(f"🚀 PFC Simulation Mode: {mode}")

    return app
