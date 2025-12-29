from flask import Blueprint, request, jsonify
from flask import jsonify
from app.models import User
from app.extensions import db
from flask_jwt_extended import create_access_token, get_jwt, jwt_required, get_jwt_identity, JWTManager
from flask_cors import cross_origin 


auth_bp = Blueprint('auth', __name__)
routes = Blueprint('routes', __name__)

jwt = JWTManager()

@jwt.unauthorized_loader
def unauthorized_callback(error):
    return jsonify({"msg": "Missing or invalid token"}), 401
# Signup route
@auth_bp.route('/signup', methods=['POST', 'OPTIONS'])
@cross_origin(origins='http://localhost:3000') 
def signup():
    if request.method == 'OPTIONS':
        return '', 204  

    data = request.json

    required_fields = ['firstname', 'lastname', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    # Check if the user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "User already exists"}), 400

    # Create a new user
    user = User(
        firstname=data['firstname'],
        lastname=data['lastname'],
        email=data['email']
    )
    user.set_password(data['password'])  # Hash the password before storing

    try:
        # Save user to the database
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))


        return jsonify({
            "message": "User created successfully",
            "user": {
                "id": user.id,
                "email": user.email
            },
            "access_token": access_token
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Login route
@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
@cross_origin(origins='http://localhost:3000')
def login():
    if request.method == 'OPTIONS':
        return '', 204  # Handle preflight OPTIONS request

    data = request.json

    # Check if the user exists
    user = User.query.filter_by(email=data['email']).first()

    # Validate user credentials
    if not user or not user.check_password(data['password']):
        return jsonify({"error": "Invalid email or password"}), 401

    # Create an access token
    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token), 200


blacklist = set()

@jwt.token_in_blocklist_loader
def check_if_token_in_blocklist(jwt_header, jwt_payload):
    return jwt_payload['jti'] in blacklist

@auth_bp.route('/logout', methods=['POST', 'OPTIONS'])
@jwt_required()
def logout():
    try:
        jti = get_jwt()["jti"]
        blacklist.add(jti)
        return jsonify({"msg": "Logout successful"}), 200
    except Exception as e:
        return jsonify({"error": f"Logout failed: {str(e)}"}), 422


# Get user route (protected)
@auth_bp.route('/api/user', methods=['GET'])
@jwt_required()
def get_user():
    user_id = get_jwt_identity()
    print("User ID from JWT:", user_id)
    user = User.query.get(user_id)
    if user:
        return jsonify({"firstname": user.firstname, "lastname": user.lastname})
    else:
        return jsonify({"msg": "User not found"}), 404



main = Blueprint('main', __name__)

