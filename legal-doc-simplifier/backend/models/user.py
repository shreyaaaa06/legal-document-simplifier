from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from bson import ObjectId
from backend.config.database import db_instance

class User(UserMixin):
    def __init__(self, email, password_hash=None, name=None, _id=None, created_at=None):
        self.id = str(_id) if _id else None
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.created_at = created_at or datetime.utcnow()
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password is correct"""
        return check_password_hash(self.password_hash, password)
    
    def save(self):
        """Save user to database"""
        db = db_instance.get_db()
        user_data = {
            'email': self.email,
            'password_hash': self.password_hash,
            'name': self.name,
            'created_at': self.created_at
        }
        
        if self.id:
            # Update existing user
            db.users.update_one(
                {'_id': ObjectId(self.id)},
                {'$set': user_data}
            )
        else:
            # Create new user
            result = db.users.insert_one(user_data)
            self.id = str(result.inserted_id)
        
        return self
    
    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        db = db_instance.get_db()
        user_data = db.users.find_one({'email': email})
        
        if user_data:
            return User(
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                name=user_data.get('name'),
                _id=user_data['_id'],
                created_at=user_data.get('created_at')
            )
        return None
    
    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        db = db_instance.get_db()
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        
        if user_data:
            return User(
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                name=user_data.get('name'),
                _id=user_data['_id'],
                created_at=user_data.get('created_at')
            )
        return None
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at
        }