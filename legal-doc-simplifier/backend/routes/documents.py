#routes/documents.py
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from backend.models.document import Document
from backend.models.clause import Clause
from backend.utils.file_handler import FileHandler
from backend.utils.auth_middleware import login_required_api
from backend.routes.agents import process_document_pipeline


documents_bp = Blueprint('documents', __name__)

@documents_bp.route('/upload', methods=['POST'])
@login_required
def upload_document():
    """Upload and process a new document"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Initialize file handler
        file_handler = FileHandler(current_app.config['UPLOAD_FOLDER'])
        
        if not file_handler.is_allowed_file(file.filename):
            return jsonify({'error': 'File type not supported'}), 400
        
        # Save file
        file_path = file_handler.save_file(file)
        
        # Extract text from file
        try:
            extracted_text = file_handler.extract_text(file_path)
            if not extracted_text.strip():
                return jsonify({'error': 'No text could be extracted from the file'}), 400
        
        except Exception as e:
            file_handler.cleanup_file(file_path)
            return jsonify({'error': f'Failed to extract text: {str(e)}'}), 400
        
        # Create document record
        document = Document(
            user_id=current_user.id,
            filename=secure_filename(file.filename),
            file_path=file_path,
            original_text=extracted_text,
            status='processing'
        )
        document.save()
        
        # Process document immediately (synchronous for debugging)
        try:
            print(f"Starting immediate processing for document {document.id}")
            result = process_document_immediately(document.id)
            print(f"Processing result: {result}")
            
        except Exception as e:
            print(f"Processing failed: {e}")
            document.update_status('failed', summary=f"Processing error: {str(e)}")
        
        # Return document info
        return jsonify({
            'message': 'Document uploaded and processed successfully',
            'document': document.to_dict(),
            'processing': False
        }), 201
    
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500
def process_document_immediately(document_id):
    """Process document synchronously for immediate results"""
    try:
        print(f"Processing document {document_id}")
        
        document = Document.find_by_id(document_id)
        if not document:
            raise Exception("Document not found")
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise Exception("Google API key not configured")
        
        # Step 1: Basic preprocessing and splitting
        from backend.agents.preprocessing_agent import PreprocessingAgent
        preprocessor = PreprocessingAgent(api_key)
        preprocessed = preprocessor.preprocess_document(document.original_text, document.filename)
        
        print(f"Preprocessed into {len(preprocessed['sections'])} sections")
        
        # Step 2: Create simplified clauses directly (without complex agents for now)
        clauses_created = 0
        
        for i, section in enumerate(preprocessed['sections']):
            # Skip very short sections
            if len(section['text'].strip()) < 50:
                continue
                
            # Basic clause classification
            clause_type = classify_clause_simple(section['text'])
            risk_level = assess_risk_simple(section['text'])
            
            # Create simplified version using AI
            simplified_text = create_simple_summary(section['text'], api_key)
            
            # Extract basic info
            deadlines = extract_dates_simple(section['text'])
            obligations = extract_obligations_simple(section['text'])
            
            # Create clause
            clause = Clause(
                document_id=document_id,
                original_text=section['text'],
                simplified_text=simplified_text,
                clause_type=clause_type,
                section_number=i + 1,
                risk_level=risk_level,
                deadlines=deadlines,
                obligations=obligations,
                advice=f"Review this {clause_type} clause carefully"
            )
            clause.save()
            clauses_created += 1
            print(f"Created clause {i+1}: {clause_type}")
        
        # Step 3: Generate document summary
        summary = generate_document_summary(preprocessed, clauses_created, api_key)
        
        # Step 4: Calculate basic risk score
        risk_score = calculate_basic_risk_score(document_id)
        
        # Update document
        document.update_status(
            'completed',
            summary=summary,
            document_type=preprocessed['document_type'],
            risk_score=risk_score
        )
        
        print(f"Processing completed. Created {clauses_created} clauses")
        return {'success': True, 'clauses_created': clauses_created}
        
    except Exception as e:
        print(f"Processing error: {e}")
        import traceback
        traceback.print_exc()
        
        # Update document status to failed
        try:
            document = Document.find_by_id(document_id)
            if document:
                document.update_status('failed', summary=f"Processing failed: {str(e)}")
        except:
            pass
        
        raise e
def classify_clause_simple(text):
    """Basic clause classification using keywords"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['must', 'shall', 'required', 'obligation', 'responsible']):
        return 'obligation'
    elif any(word in text_lower for word in ['penalty', 'fine', 'damages', 'breach']):
        return 'penalty'
    elif any(word in text_lower for word in ['deadline', 'date', 'within', 'days', 'months']):
        return 'deadline'
    elif any(word in text_lower for word in ['risk', 'liable', 'danger', 'loss']):
        return 'risk'
    elif any(word in text_lower for word in ['right', 'entitled', 'benefit']):
        return 'right'
    else:
        return 'general'

def assess_risk_simple(text):
    """Basic risk assessment"""
    text_lower = text.lower()
    
    high_risk_words = ['penalty', 'fine', 'breach', 'terminate', 'damages', 'liable', 'lawsuit']
    medium_risk_words = ['deadline', 'obligation', 'must', 'required', 'responsibility']
    
    if any(word in text_lower for word in high_risk_words):
        return 'high'
    elif any(word in text_lower for word in medium_risk_words):
        return 'medium'
    else:
        return 'low'

def create_simple_summary(text, api_key):
    """Create simplified version of text"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Simplify this legal text into plain English that anyone can understand. Keep it concise but include all important details:
        
        {text}
        
        Simplified version:
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"Simplification failed: {e}")
        # Return original text if simplification fails
        return text

def extract_dates_simple(text):
    """Extract dates and deadlines"""
    import re
    
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        r'\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{2,4}\b',
        r'within\s+\d+\s+days',
        r'within\s+\d+\s+months'
    ]
    
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates.extend(matches)
    
    return dates[:3]  # Limit to 3 dates

def extract_obligations_simple(text):
    """Extract key obligations"""
    import re
    
    # Look for sentences with obligation keywords
    sentences = text.split('.')
    obligations = []
    
    obligation_keywords = ['must', 'shall', 'required', 'responsible', 'obligation', 'duty']
    
    for sentence in sentences:
        if any(keyword in sentence.lower() for keyword in obligation_keywords):
            clean_sentence = sentence.strip()
            if len(clean_sentence) > 20:
                obligations.append(clean_sentence)
                if len(obligations) >= 3:  # Limit to 3 obligations
                    break
    
    return obligations

def generate_document_summary(preprocessed, clauses_count, api_key):
    """Generate overall document summary"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Use first 2000 characters for summary
        text_sample = preprocessed['cleaned_text'][:2000]
        
        prompt = f"""
        Create a brief summary (2-3 sentences) of this {preprocessed['document_type']} document:
        
        {text_sample}
        
        Summary:
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"Summary generation failed: {e}")
        return f"This is a {preprocessed['document_type']} document with {clauses_count} analyzed sections."

def calculate_basic_risk_score(document_id):
    """Calculate basic risk score based on clauses"""
    try:
        clauses = Clause.find_by_document_id(document_id)
        if not clauses:
            return 0
        
        risk_weights = {'low': 1, 'medium': 2, 'high': 3}
        total_weight = sum(risk_weights.get(clause.risk_level, 1) for clause in clauses)
        max_possible = len(clauses) * 3
        
        return int((total_weight / max_possible) * 100) if max_possible > 0 else 0
        
    except Exception as e:
        print(f"Risk calculation failed: {e}")
        return 0





@documents_bp.route('/', methods=['GET'])
@login_required
def get_documents():
    """Get all documents for the current user"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # For now, just get all documents (pagination can be added later)
        documents = Document.find_by_user_id(current_user.id, limit=per_page)
        
        documents_data = []
        for doc in documents:
            doc_data = doc.to_dict()
            
            # Get clause count for each document
            clauses = Clause.find_by_document_id(doc.id)
            doc_data['clause_count'] = len(clauses)
            doc_data['risk_summary'] = {
                'high_risk_clauses': len([c for c in clauses if c.risk_level == 'high']),
                'deadlines': len([c for c in clauses if c.clause_type == 'deadline' or c.deadlines])
            }
            
            documents_data.append(doc_data)
        
        return jsonify({
            'documents': documents_data,
            'total': len(documents_data)
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get documents: {str(e)}'}), 500

@documents_bp.route('/<document_id>', methods=['GET'])
@login_required
def get_document(document_id):
    """Get a specific document with its clauses"""
    try:
        document = Document.find_by_id(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        if document.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get associated clauses
        clauses = Clause.find_by_document_id(document_id)
        
        doc_data = document.to_dict()
        doc_data['clauses'] = [clause.to_dict() for clause in clauses]
        
        # Add some analytics
        doc_data['analytics'] = {
            'total_clauses': len(clauses),
            'clause_types': {},
            'risk_levels': {'low': 0, 'medium': 0, 'high': 0}
        }
        
        for clause in clauses:
            # Count clause types
            clause_type = clause.clause_type
            doc_data['analytics']['clause_types'][clause_type] = \
                doc_data['analytics']['clause_types'].get(clause_type, 0) + 1
            
            # Count risk levels
            risk_level = clause.risk_level
            if risk_level in doc_data['analytics']['risk_levels']:
                doc_data['analytics']['risk_levels'][risk_level] += 1
        
        return jsonify(doc_data), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get document: {str(e)}'}), 500

@documents_bp.route('/<document_id>', methods=['DELETE'])
@login_required
def delete_document(document_id):
    """Delete a document and its associated data"""
    try:
        document = Document.find_by_id(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        if document.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Delete associated clauses first
        from backend.config.database import db_instance
        db = db_instance.get_db()
        from bson import ObjectId
        
        db.clauses.delete_many({'document_id': document_id})
        
        # Delete the document
        db.documents.delete_one({'_id': ObjectId(document_id)})
        
        # Clean up the file
        file_handler = FileHandler(current_app.config['UPLOAD_FOLDER'])
        file_handler.cleanup_file(document.file_path)
        
        return jsonify({'message': 'Document deleted successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to delete document: {str(e)}'}), 500

@documents_bp.route('/<document_id>/clauses', methods=['GET'])
@login_required
def get_document_clauses(document_id):
    """Get clauses for a specific document with filtering options"""
    try:
        document = Document.find_by_id(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        if document.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get query parameters for filtering
        clause_type = request.args.get('type')
        risk_level = request.args.get('risk_level')
        
        clauses = Clause.find_by_document_id(document_id)
        
        # Filter clauses if parameters provided
        if clause_type:
            clauses = [c for c in clauses if c.clause_type == clause_type]
        
        if risk_level:
            clauses = [c for c in clauses if c.risk_level == risk_level]
        
        clauses_data = [clause.to_dict() for clause in clauses]
        
        return jsonify({
            'clauses': clauses_data,
            'total': len(clauses_data),
            'filters_applied': {
                'type': clause_type,
                'risk_level': risk_level
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get clauses: {str(e)}'}), 500

@documents_bp.route('/<document_id>/summary', methods=['GET'])
@login_required
def get_document_summary(document_id):
    """Get document summary and key insights"""
    try:
        document = Document.find_by_id(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        if document.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        clauses = Clause.find_by_document_id(document_id)
        
        # Generate summary data
        summary = {
            'document_info': document.to_dict(),
            'total_clauses': len(clauses),
            'clause_breakdown': {},
            'risk_analysis': {
                'overall_risk_score': document.risk_score,
                'high_risk_clauses': [],
                'deadlines': [],
                'key_obligations': []
            },
            'key_highlights': []
        }
        
        # Analyze clauses
        for clause in clauses:
            clause_type = clause.clause_type
            summary['clause_breakdown'][clause_type] = \
                summary['clause_breakdown'].get(clause_type, 0) + 1
            
            # Collect high-risk clauses
            if clause.risk_level == 'high':
                summary['risk_analysis']['high_risk_clauses'].append({
                    'section': clause.section_number,
                    'text': clause.simplified_text[:200] + "...",
                    'type': clause.clause_type
                })
            
            # Collect deadlines
            if clause.deadlines or clause.clause_type == 'deadline':
                summary['risk_analysis']['deadlines'].append({
                    'section': clause.section_number,
                    'text': clause.simplified_text[:200] + "...",
                    'deadlines': clause.deadlines
                })
            
            # Collect key obligations
            if clause.clause_type == 'obligation' or clause.obligations:
                summary['risk_analysis']['key_obligations'].append({
                    'section': clause.section_number,
                    'text': clause.simplified_text[:200] + "...",
                    'obligations': clause.obligations
                })
        
        return jsonify(summary), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get summary: {str(e)}'}), 500

@documents_bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard_data():
    """Get dashboard overview data for the user"""
    try:
        # Get user's documents
        documents = Document.find_by_user_id(current_user.id)
        
        dashboard_data = {
            'total_documents': len(documents),
            'processing_documents': len([d for d in documents if d.status == 'processing']),
            'completed_documents': len([d for d in documents if d.status == 'completed']),
            'recent_documents': [],
            'upcoming_deadlines': [],  # We'll populate this
            'high_risk_alerts': [],    # We'll populate this
            'document_types': {},
            'overall_stats': {
                'total_clauses': 0,
                'high_risk_clauses': 0,
                'total_deadlines': 0,
                'avg_risk_score': 0
            }
        }
        
        # Process recent documents AND extract deadlines/risks
        recent_docs = documents[:5]  # Get 5 most recent
        total_risk_score = 0
        
        for doc in recent_docs:
            doc_data = doc.to_dict()
            clauses = Clause.find_by_document_id(doc.id)
            
            doc_data['clause_count'] = len(clauses)
            doc_data['high_risk_count'] = len([c for c in clauses if c.risk_level == 'high'])
            
            dashboard_data['recent_documents'].append(doc_data)
            
            # Extract deadlines from clauses
            for clause in clauses:
                if clause.deadlines and len(clause.deadlines) > 0:
                    for deadline in clause.deadlines:
                        dashboard_data['upcoming_deadlines'].append({
                            'deadline': deadline,
                            'description': f"{doc.filename} - Section {clause.section_number}",
                            'document_name': doc.filename,
                            'section': clause.section_number,
                            'urgency': 'medium'  # Default urgency
                        })
                
                # Extract high-risk alerts
                if clause.risk_level == 'high':
                    dashboard_data['high_risk_alerts'].append({
                        'description': clause.simplified_text[:100] + "...",
                        'section': clause.section_number,
                        'document_name': doc.filename,
                        'risk_level': 'high'
                    })
            
            # Update stats
            dashboard_data['overall_stats']['total_clauses'] += len(clauses)
            dashboard_data['overall_stats']['high_risk_clauses'] += doc_data['high_risk_count']
            
            # Count document types
            doc_type = doc.document_type or 'Unknown'
            dashboard_data['document_types'][doc_type] = \
                dashboard_data['document_types'].get(doc_type, 0) + 1
            
            if doc.risk_score:
                total_risk_score += doc.risk_score
        
        # Calculate average risk score
        if len(documents) > 0:
            dashboard_data['overall_stats']['avg_risk_score'] = \
                total_risk_score / len(documents)
        
        # Limit results
        dashboard_data['upcoming_deadlines'] = dashboard_data['upcoming_deadlines'][:10]
        dashboard_data['high_risk_alerts'] = dashboard_data['high_risk_alerts'][:10]
        
        return jsonify(dashboard_data), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get dashboard data: {str(e)}'}), 500