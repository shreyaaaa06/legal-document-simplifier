# app.py
from flask import Flask, render_template, send_from_directory
from flask_login import LoginManager
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Import models and routes
from backend.config.database import db_instance
from backend.models.user import User
from backend.routes.auth import auth_bp
from backend.routes.documents import documents_bp
from backend.routes.agents import agents_bp

# Load environment variables
load_dotenv()

def create_app():
    """Application factory"""
    app = Flask(__name__, 
                template_folder='../frontend/templates',
                static_folder='../frontend/static')
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    app.config['MONGODB_URI'] = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/legal_doc_simplifier')
    app.config['GOOGLE_API_KEY'] = os.getenv('GOOGLE_API_KEY')
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'frontend/uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    CORS(app, supports_credentials=True)
    
    # Initialize database
    db_instance.initialize(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.find_by_id(user_id)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(agents_bp, url_prefix='/api/agents')
    
    # Frontend routes
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/login')
    def login_page():
        return render_template('login.html')
    
    @app.route('/register')
    def register_page():
        return render_template('register.html')
    
    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/upload')
    def upload_page():
        return render_template('upload.html')
    
    @app.route('/document/<document_id>')
    def document_analysis(document_id):
        return render_template('document_analysis.html', document_id=document_id)
    
    # Serve uploaded files (for development only)
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('index.html'), 404
    
    @app.errorhandler(413)
    def file_too_large(error):
        return {'error': 'File too large. Maximum size is 16MB.'}, 413
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    @app.route('/chat-history')
    def chat_history():
        return render_template('chat_history.html')
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    # Check if required environment variables are set
    if not app.config['GOOGLE_API_KEY']:
        print("WARNING: GOOGLE_API_KEY not set. AI features will not work.")
    
    print("Starting Legal Document Simplifier...")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Database URI: {app.config['MONGODB_URI']}")
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )