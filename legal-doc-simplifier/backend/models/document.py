# models/document.py
from datetime import datetime
from bson import ObjectId
from backend.config.database import db_instance

class Document:
    def __init__(self, user_id, filename, file_path, original_text, document_type=None, 
                 summary=None, risk_score=0, status='processing', _id=None, created_at=None):
        self.id = str(_id) if _id else None
        self.user_id = user_id
        self.filename = filename
        self.file_path = file_path
        self.original_text = original_text
        self.document_type = document_type
        self.summary = summary
        self.risk_score = risk_score
        self.status = status  # processing, completed, failed
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def save(self):
        """Save document to database"""
        db = db_instance.get_db()
        doc_data = {
            'user_id': self.user_id,
            'filename': self.filename,
            'file_path': self.file_path,
            'original_text': self.original_text,
            'document_type': self.document_type,
            'summary': self.summary,
            'risk_score': self.risk_score,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        if self.id:
            # Update existing document
            db.documents.update_one(
                {'_id': ObjectId(self.id)},
                {'$set': doc_data}
            )
        else:
            # Create new document
            result = db.documents.insert_one(doc_data)
            self.id = str(result.inserted_id)
        
        return self
    
    @staticmethod
    def find_by_user_id(user_id, limit=None):
        """Find documents by user ID"""
        db = db_instance.get_db()
        cursor = db.documents.find({'user_id': user_id}).sort('created_at', -1)
        
        if limit:
            cursor = cursor.limit(limit)
        
        documents = []
        for doc_data in cursor:
            documents.append(Document(
                user_id=doc_data['user_id'],
                filename=doc_data['filename'],
                file_path=doc_data['file_path'],
                original_text=doc_data['original_text'],
                document_type=doc_data.get('document_type'),
                summary=doc_data.get('summary'),
                risk_score=doc_data.get('risk_score', 0),
                status=doc_data.get('status', 'processing'),
                _id=doc_data['_id'],
                created_at=doc_data.get('created_at')
            ))
        
        return documents
    
    @staticmethod
    def find_by_id(doc_id):
        """Find document by ID"""
        db = db_instance.get_db()
        doc_data = db.documents.find_one({'_id': ObjectId(doc_id)})
        
        if doc_data:
            return Document(
                user_id=doc_data['user_id'],
                filename=doc_data['filename'],
                file_path=doc_data['file_path'],
                original_text=doc_data['original_text'],
                document_type=doc_data.get('document_type'),
                summary=doc_data.get('summary'),
                risk_score=doc_data.get('risk_score', 0),
                status=doc_data.get('status', 'processing'),
                _id=doc_data['_id'],
                created_at=doc_data.get('created_at')
            )
        return None
    
    def update_status(self, status, summary=None, document_type=None, risk_score=None):
        """Update document status and related fields"""
        self.status = status
        self.updated_at = datetime.utcnow()
        
        if summary:
            self.summary = summary
        if document_type:
            self.document_type = document_type
        if risk_score is not None:
            self.risk_score = risk_score
        
        return self.save()
    
    def to_dict(self):
        """Convert document to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'document_type': self.document_type,
            'summary': self.summary,
            'risk_score': self.risk_score,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }