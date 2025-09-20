from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import os
from backend.models.document import Document
from backend.models.clause import Clause
from backend.agents.preprocessing_agent import PreprocessingAgent
from backend.agents.classification_agent import ClauseClassificationAgent
from backend.agents.simplification_agent import SimplificationAgent
from backend.agents.risk_analysis_agent import RiskAnalysisAgent
from backend.agents.qa_agent import QAAgent
from backend.utils.auth_middleware import login_required_api, validate_json_data
from backend.models.conversation import Conversation

agents_bp = Blueprint('agents', __name__)

# Initialize agents
def get_agents():
    """Get initialized agent instances"""
    api_key = current_app.config.get('GOOGLE_API_KEY')
    if not api_key:
        raise Exception("Google API key not configured")
    
    return {
        'preprocessing': PreprocessingAgent(api_key),
        'classification': ClauseClassificationAgent(api_key),
        'simplification': SimplificationAgent(api_key),
        'risk_analysis': RiskAnalysisAgent(api_key),
        'qa': QAAgent(api_key)
    }

@agents_bp.route('/process-document/<document_id>', methods=['POST'])
@login_required
def process_document(document_id):
    """Process a document through the multi-agent pipeline"""
    try:
        # Get document
        document = Document.find_by_id(document_id)
        if not document or document.user_id != current_user.id:
            return jsonify({'error': 'Document not found or access denied'}), 404
        
        if document.status == 'completed':
            return jsonify({'message': 'Document already processed'}), 200
        
        # Get processing options
        data = request.get_json() or {}
        simplification_level = data.get('simplification_level', 'general')
        
        # Initialize agents
        agents = get_agents()
        
        # Step 1: Preprocessing
        preprocessing_result = agents['preprocessing'].preprocess_document(
            document.original_text, 
            document.filename
        )
        
        # Update document with basic info
        document.update_status(
            'processing', 
            document_type=preprocessing_result['document_type']
        )
        
        # Step 2: Classification
        classified_clauses = agents['classification'].classify_clauses(
            preprocessing_result['sections']
        )
        
        # Step 3: Simplification
        simplified_clauses = agents['simplification'].simplify_clauses(
            classified_clauses, 
            simplification_level
        )
        
        # Step 4: Risk Analysis
        risk_analysis = agents['risk_analysis'].analyze_document_risks(
            simplified_clauses, 
            preprocessing_result['document_type']
        )
        
        # Step 5: Generate Summary
        summary = agents['simplification'].generate_document_summary(
            simplified_clauses, 
            preprocessing_result['document_type']
        )
        
        # Save clauses to database
        for clause_data in simplified_clauses:
            clause = Clause(
                document_id=document_id,
                original_text=clause_data['text'],
                simplified_text=clause_data['simplified_text'],
                clause_type=clause_data['clause_type'],
                section_number=clause_data['section_number'],
                risk_level=clause_data['risk_level'],
                deadlines=clause_data.get('deadlines_found', []),
                obligations=clause_data.get('obligations_found', []),
                advice=risk_analysis.get('recommendations', [])
            )
            clause.save()
        
        # Update document status
        document.update_status(
            'completed',
            summary=summary,
            risk_score=risk_analysis['overall_risk_score']
        )
        
        return jsonify({
            'message': 'Document processed successfully',
            'document': document.to_dict(),
            'processing_results': {
                'total_sections': len(preprocessing_result['sections']),
                'total_clauses': len(simplified_clauses),
                'risk_score': risk_analysis['overall_risk_score'],
                'document_type': preprocessing_result['document_type']
            },
            'risk_analysis': risk_analysis
        }), 200
    
    except Exception as e:
        # Update document status to failed
        try:
            document.update_status('failed')
        except:
            pass
        
        return jsonify({'error': f'Document processing failed: {str(e)}'}), 500

@agents_bp.route('/ask-question', methods=['POST'])
@login_required
@validate_json_data(['question'])
def ask_question():
    try:
        data = request.get_json()
        question = data['question']
        document_id = data.get('document_id')
        conversation_id = data.get('conversation_id')
        
        print(f"DEBUG: Question='{question}', DocumentID='{document_id}', UserID='{current_user.id}', ConversationID='{conversation_id}'")
        
        # Initialize QA agent
        agents = get_agents()
        qa_agent = agents['qa']
        
        # Get answer with conversation history
        answer_data = qa_agent.answer_question(question, str(current_user.id), document_id, conversation_id)
        
        print(f"DEBUG: Answer data: {answer_data}")
        
        return jsonify(answer_data), 200
    
    except Exception as e:
        print(f"DEBUG: QA Route error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to process question: {str(e)}'}), 500

@agents_bp.route('/suggested-questions', methods=['GET'])
@login_required
def get_suggested_questions():
    """Get suggested questions based on user's documents"""
    try:
        document_id = request.args.get('document_id')
        
        # Initialize QA agent
        agents = get_agents()
        qa_agent = agents['qa']
        
        suggestions = qa_agent.get_suggested_questions(current_user.id, document_id)
        
        return jsonify({'suggestions': suggestions}), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get suggestions: {str(e)}'}), 500

@agents_bp.route('/re-simplify/<document_id>', methods=['POST'])
@login_required
@validate_json_data(['simplification_level'])
def re_simplify_document(document_id):
    """Re-simplify a document with a different complexity level"""
    try:
        # Get document
        document = Document.find_by_id(document_id)
        if not document or document.user_id != current_user.id:
            return jsonify({'error': 'Document not found or access denied'}), 404
        
        data = request.get_json()
        new_level = data['simplification_level']
        
        if new_level not in ['general', 'student', 'professional', 'lawyer']:
            return jsonify({'error': 'Invalid simplification level'}), 400
        
        # Get existing clauses
        clauses = Clause.find_by_document_id(document_id)
        if not clauses:
            return jsonify({'error': 'No clauses found to re-simplify'}), 404
        
        # Initialize simplification agent
        agents = get_agents()
        simplification_agent = agents['simplification']
        
        # Prepare clauses for re-simplification
        classified_clauses = []
        for clause in clauses:
            clause_data = clause.to_dict()
            clause_data['text'] = clause_data['original_text']  # Use original text
            classified_clauses.append(clause_data)
        
        # Re-simplify with new level
        re_simplified = simplification_agent.simplify_clauses(classified_clauses, new_level)
        
        # Update clauses in database
        from backend.config.database import db_instance
        db = db_instance.get_db()
        from bson import ObjectId
        
        for clause_data in re_simplified:
            db.clauses.update_one(
                {'_id': ObjectId(clause_data['id'])},
                {'$set': {'simplified_text': clause_data['simplified_text']}}
            )
        
        # Generate new summary
        new_summary = simplification_agent.generate_document_summary(
            re_simplified, 
            document.document_type
        )
        
        # Update document summary
        document.summary = new_summary
        document.save()
        
        return jsonify({
            'message': 'Document re-simplified successfully',
            'new_level': new_level,
            'summary': new_summary
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Re-simplification failed: {str(e)}'}), 500

@agents_bp.route('/analyze-risks/<document_id>', methods=['POST'])
@login_required
def analyze_document_risks(document_id):
    """Perform detailed risk analysis on a document"""
    try:
        # Get document and clauses
        document = Document.find_by_id(document_id)
        if not document or document.user_id != current_user.id:
            return jsonify({'error': 'Document not found or access denied'}), 404
        
        clauses = Clause.find_by_document_id(document_id)
        if not clauses:
            return jsonify({'error': 'No clauses found for analysis'}), 404
        
        # Initialize risk analysis agent
        agents = get_agents()
        risk_agent = agents['risk_analysis']
        
        # Prepare clause data
        simplified_clauses = [clause.to_dict() for clause in clauses]
        
        # Perform detailed risk analysis
        risk_analysis = risk_agent.analyze_document_risks(
            simplified_clauses, 
            document.document_type
        )
        
        # Extract critical dates
        critical_dates = risk_agent.extract_critical_dates(simplified_clauses)
        
        # Add critical dates to response
        risk_analysis['critical_dates'] = critical_dates
        
        return jsonify({
            'document_id': document_id,
            'document_type': document.document_type,
            'risk_analysis': risk_analysis
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Risk analysis failed: {str(e)}'}), 500

@agents_bp.route('/process-status/<document_id>', methods=['GET'])
@login_required
def get_processing_status(document_id):
    """Get the processing status of a document"""
    try:
        document = Document.find_by_id(document_id)
        if not document or document.user_id != current_user.id:
            return jsonify({'error': 'Document not found or access denied'}), 404
        
        # Get clause count to determine processing progress
        clauses = Clause.find_by_document_id(document_id)
        
        status_info = {
            'document_id': document_id,
            'status': document.status,
            'filename': document.filename,
            'document_type': document.document_type,
            'risk_score': document.risk_score,
            'created_at': document.created_at,
            'updated_at': document.updated_at,
            'clauses_processed': len(clauses),
            'has_summary': bool(document.summary)
        }
        
        if document.status == 'completed':
            status_info['processing_complete'] = True
        elif document.status == 'processing':
            status_info['processing_complete'] = False
            status_info['estimated_completion'] = 'Processing...'
        else:
            status_info['processing_complete'] = False
            status_info['error'] = True
        
        return jsonify(status_info), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500
@agents_bp.route('/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get all conversations for the current user"""
    try:
        conversations = Conversation.find_by_user_and_document(
            user_id=str(current_user.id),
            document_id=None,  # Get all conversations
            limit=None
        )
        
        # Get document names for conversations
        conversations_data = []
        for conv in conversations:
            conv_dict = conv.to_dict()
            conv_dict['message_count'] = len(conv.messages)
            
            # Get document name if conversation is linked to a document
            if conv.document_id:
                doc = Document.find_by_id(conv.document_id)
                conv_dict['document_name'] = doc.filename if doc else 'Unknown Document'
            else:
                conv_dict['document_name'] = None
                
            conversations_data.append(conv_dict)
        
        return jsonify({'conversations': conversations_data}), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get conversations: {str(e)}'}), 500

@agents_bp.route('/conversations', methods=['POST'])
@login_required
def create_conversation():
    """Create a new conversation"""
    try:
        data = request.get_json() or {}
        document_id = data.get('document_id')
        
        conversation = Conversation(
            user_id=str(current_user.id),
            document_id=document_id
        )
        conversation.save()
        
        conv_dict = conversation.to_dict()
        conv_dict['message_count'] = 0
        conv_dict['document_name'] = None
        
        if document_id:
            doc = Document.find_by_id(document_id)
            conv_dict['document_name'] = doc.filename if doc else 'Unknown Document'
        
        return jsonify({'conversation': conv_dict}), 201
    
    except Exception as e:
        return jsonify({'error': f'Failed to create conversation: {str(e)}'}), 500

@agents_bp.route('/conversations/<conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    """Get a specific conversation"""
    try:
        conversation = Conversation.find_by_id(conversation_id)
        
        if not conversation or conversation.user_id != str(current_user.id):
            return jsonify({'error': 'Conversation not found or access denied'}), 404
        
        conv_dict = conversation.to_dict()
        conv_dict['message_count'] = len(conversation.messages)
        
        # Get document name if conversation is linked to a document
        if conversation.document_id:
            doc = Document.find_by_id(conversation.document_id)
            conv_dict['document_name'] = doc.filename if doc else 'Unknown Document'
        else:
            conv_dict['document_name'] = None
            
        return jsonify(conv_dict), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get conversation: {str(e)}'}), 500

@agents_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        conversation = Conversation.find_by_id(conversation_id)
        
        if not conversation or conversation.user_id != str(current_user.id):
            return jsonify({'error': 'Conversation not found or access denied'}), 404
        
        # Delete from database
        from backend.config.database import db_instance
        db = db_instance.get_db()
        from bson import ObjectId
        
        db.conversations.delete_one({'_id': ObjectId(conversation_id)})
        
        return jsonify({'message': 'Conversation deleted successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to delete conversation: {str(e)}'}), 500
@agents_bp.route('/calendar/deadlines', methods=['GET'])
@login_required
def get_user_deadlines():
    """Get all deadlines for calendar view"""
    try:
        month = request.args.get('month')  # Format: 2025-03
        document_id = request.args.get('document_id')
        
        # Get deadlines from clauses
        clauses = Clause.find_user_deadlines_with_dates(str(current_user.id))
        
        calendar_events = []
        for clause in clauses:
            for deadline_text in clause.deadlines:
                parsed_date = parse_deadline_to_date(deadline_text, clause.document_id)
                if parsed_date:
                    calendar_events.append({
                        'date': parsed_date.isoformat(),
                        'title': deadline_text,
                        'type': 'deadline',
                        'urgency': get_deadline_urgency(parsed_date),
                        'document_id': clause.document_id,
                        'section': clause.section_number
                    })
        
        return jsonify({'deadlines': calendar_events}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get deadlines: {str(e)}'}), 500

@agents_bp.route('/ask-calendar', methods=['POST'])
@login_required
@validate_json_data(['question'])
def ask_calendar_question():
    """Handle calendar-related questions"""
    try:
        data = request.get_json()
        question = data['question']
        
        # Check if question is calendar-related
        calendar_keywords = ['calendar', 'deadline', 'due', 'payment', 'when', 'schedule']
        
        if any(keyword in question.lower() for keyword in calendar_keywords):
            # Get user's deadlines
            deadlines_response = get_user_deadlines()
            # Return calendar data or answer about deadlines
            return jsonify({
                'show_calendar': True,
                'deadlines': deadlines_response[0].json['deadlines'] if deadlines_response[1] == 200 else []
            }), 200
        else:
            # Regular Q&A processing
            return ask_question()
            
    except Exception as e:
        return jsonify({'error': f'Failed to process calendar question: {str(e)}'}), 500

def process_document_pipeline(document_id):
    """Background processing pipeline for documents"""
    try:
        print(f"Starting processing for document {document_id}")
        document = Document.find_by_id(document_id)
        if not document:
            print(f"Document {document_id} not found")
            return
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("No API key found")
            document.update_status('failed', summary="API key not configured")
            return
        
        # Step 1: Preprocess
        print("Step 1: Preprocessing...")
        preprocessor = PreprocessingAgent(api_key)
        preprocessed = preprocessor.preprocess_document(document.original_text, document.filename)
        
        # Step 2: Classify clauses
        print("Step 2: Classifying clauses...")
        classifier = ClauseClassificationAgent(api_key)
        classified_clauses = classifier.classify_clauses(preprocessed['sections'])
        print(f"Classified {len(classified_clauses)} clauses")
        
        # Step 3: Simplify clauses
        print("Step 3: Simplifying clauses...")
        simplifier = SimplificationAgent(api_key)
        simplified_clauses = simplifier.simplify_clauses(classified_clauses, 'general')
        
        # Step 4: Generate summary
        print("Step 4: Generating summary...")
        summary = simplifier.generate_document_summary(simplified_clauses, preprocessed['document_type'])
        
        # Step 5: Analyze risks
        print("Step 5: Analyzing risks...")
        risk_analyzer = RiskAnalysisAgent(api_key)
        risk_analysis = risk_analyzer.analyze_document_risks(simplified_clauses, preprocessed['document_type'])
        
        # Step 6: Save clauses to database
        print("Step 6: Saving clauses...")
        for clause_data in simplified_clauses:
            # Extract deadlines from clause text
            extracted_deadlines = extract_deadlines_from_text(clause_data['simplified_text'])
            
            clause = Clause(
                document_id=document_id,
                original_text=clause_data['text'],
                simplified_text=clause_data['simplified_text'],
                clause_type=clause_data['clause_type'],
                section_number=clause_data['section_number'],
                risk_level=clause_data['risk_level'],
                deadlines=extracted_deadlines,  # Use extracted deadlines
                obligations=clause_data.get('obligations_found', []),
                advice="; ".join(risk_analysis.get('recommendations', [])[:2])
            )
            clause.save()
            print(f"Saved clause {clause_data['section_number']}: {clause_data['clause_type']}")
        
        # Step 7: Update document status with summary and risk score
        print("Step 7: Updating document...")
        document.update_status(
            'completed', 
            summary=summary,  # Now includes actual summary
            document_type=preprocessed['document_type'],
            risk_score=risk_analysis['overall_risk_score']
        )
        
        print(f"Processing completed for document {document_id}")
        
    except Exception as e:
        print(f"Processing failed for document {document_id}: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            document = Document.find_by_id(document_id)
            if document:
                document.update_status('failed', summary=f"Processing error: {str(e)}")
        except:
            pass

def calculate_risk_score(clauses):
    """Calculate overall risk score"""
    if not clauses:
        return 0
    
    risk_weights = {'low': 1, 'medium': 2, 'high': 3}
    total_weight = sum(risk_weights.get(clause['risk_level'], 1) for clause in clauses)
    max_possible = len(clauses) * 3
    
    return int((total_weight / max_possible) * 100) if max_possible > 0 else 0
def extract_deadlines_from_text(text):
    """Extract deadline text from clause text"""
    deadline_keywords = [
        'due by', 'due on', 'within', 'before', 'after', 'deadline',
        'must be completed', 'required by', 'payment due', 'expires on'
    ]
    
    deadlines = []
    text_lower = text.lower()
    
    for keyword in deadline_keywords:
        if keyword in text_lower:
            # Find sentences containing deadline keywords
            sentences = text.split('.')
            for sentence in sentences:
                if keyword in sentence.lower():
                    # Clean and add the sentence as a deadline
                    clean_sentence = sentence.strip()
                    if clean_sentence and len(clean_sentence) > 10:
                        deadlines.append(clean_sentence)
                        break  # Only take first match per keyword
    
    return deadlines[:3]  # Limit to 3 deadlines per clause