from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from backend.models.user import User
from backend.utils.auth_middleware import validate_json_data

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
@validate_json_data(['email', 'password'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        email = data['email'].lower().strip()
        password = data['password']
        name = data.get('name', '').strip()
        
        # Validate input
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Check if user already exists
        existing_user = User.find_by_email(email)
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 400
        
        # Create new user
        user = User(email=email, name=name)
        user.set_password(password)
        user.save()
        
        # Log in the user
        login_user(user, remember=True)
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
@validate_json_data(['email', 'password'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user
        user = User.find_by_email(email)
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check password
        if not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Log in user
        login_user(user, remember=data.get('remember', False))
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    try:
        logout_user()
        return jsonify({'message': 'Logout successful'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Logout failed: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get user profile"""
    try:
        return jsonify({
            'user': current_user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        
        if 'name' in data:
            current_user.name = data['name'].strip()
        
        if 'email' in data:
            new_email = data['email'].lower().strip()
            if new_email != current_user.email:
                # Check if email is already taken
                existing_user = User.find_by_email(new_email)
                if existing_user:
                    return jsonify({'error': 'Email already taken'}), 400
                current_user.email = new_email
        
        current_user.save()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@login_required
@validate_json_data(['current_password', 'new_password'])
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Validate current password
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Validate new password
        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters'}), 400
        
        # Update password
        current_user.set_password(new_password)
        current_user.save()
        
        return jsonify({'message': 'Password changed successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to change password: {str(e)}'}), 500

@auth_bp.route('/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        }), 200
    else:
        return jsonify({'authenticated': False}), 200