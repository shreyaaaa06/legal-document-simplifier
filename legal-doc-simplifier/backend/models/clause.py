from datetime import datetime
from bson import ObjectId
from backend.config.database import db_instance

class Clause:
    def __init__(self, document_id, original_text, simplified_text, clause_type, 
                 section_number=None, risk_level='low', deadlines=None, obligations=None, 
                 advice=None, _id=None, created_at=None):
        self.id = str(_id) if _id else None
        self.document_id = document_id
        self.original_text = original_text
        self.simplified_text = simplified_text
        self.clause_type = clause_type  # obligation, right, risk, penalty, deadline, general
        self.section_number = section_number
        self.risk_level = risk_level  # low, medium, high
        self.deadlines = deadlines or []
        self.obligations = obligations or []
        self.advice = advice
        self.created_at = created_at or datetime.utcnow()
    
    def save(self):
        """Save clause to database"""
        db = db_instance.get_db()
        clause_data = {
            'document_id': self.document_id,
            'original_text': self.original_text,
            'simplified_text': self.simplified_text,
            'clause_type': self.clause_type,
            'section_number': self.section_number,
            'risk_level': self.risk_level,
            'deadlines': self.deadlines,
            'obligations': self.obligations,
            'advice': self.advice,
            'created_at': self.created_at
        }
        
        if self.id:
            # Update existing clause
            db.clauses.update_one(
                {'_id': ObjectId(self.id)},
                {'$set': clause_data}
            )
        else:
            # Create new clause
            result = db.clauses.insert_one(clause_data)
            self.id = str(result.inserted_id)
        
        return self
    
    @staticmethod
    def find_by_document_id(document_id):
        """Find clauses by document ID"""
        db = db_instance.get_db()
        clauses = []
        query = {'document_id': document_id}
        if isinstance(document_id, str) and len(document_id) == 24:
            # Also try as ObjectId
            try:
                query = {'$or': [
                    {'document_id': document_id},
                    {'document_id': ObjectId(document_id)}
                ]}
            except:
                query = {'document_id': document_id}
        
        for clause_data in db.clauses.find({'document_id': document_id}):
            clauses.append(Clause(
                document_id=clause_data['document_id'],
                original_text=clause_data['original_text'],
                simplified_text=clause_data['simplified_text'],
                clause_type=clause_data['clause_type'],
                section_number=clause_data.get('section_number'),
                risk_level=clause_data.get('risk_level', 'low'),
                deadlines=clause_data.get('deadlines', []),
                obligations=clause_data.get('obligations', []),
                advice=clause_data.get('advice'),
                _id=clause_data['_id'],
                created_at=clause_data.get('created_at')
            ))
        
        return clauses
    
    @staticmethod
    def find_by_user_deadlines(user_id):
        """Find all deadlines for a user across all documents"""
        db = db_instance.get_db()
        
        # Aggregate pipeline to get clauses with deadlines for user's documents
        pipeline = [
            {
                '$lookup': {
                    'from': 'documents',
                    'localField': 'document_id',
                    'foreignField': '_id',
                    'as': 'document'
                }
            },
            {
                '$match': {
                    'document.user_id': user_id,
                    'deadlines': {'$exists': True, '$ne': []}
                }
            }
        ]
        
        deadlines = []
        for result in db.clauses.aggregate(pipeline):
            clause = Clause(
                document_id=result['document_id'],
                original_text=result['original_text'],
                simplified_text=result['simplified_text'],
                clause_type=result['clause_type'],
                section_number=result.get('section_number'),
                risk_level=result.get('risk_level', 'low'),
                deadlines=result.get('deadlines', []),
                obligations=result.get('obligations', []),
                advice=result.get('advice'),
                _id=result['_id'],
                created_at=result.get('created_at')
            )
            deadlines.append(clause)
        
        return deadlines
    @staticmethod
    def find_user_deadlines_with_dates(user_id, start_date=None, end_date=None):
        """Find all deadlines for a user with parsed dates"""
        db = db_instance.get_db()
        
        pipeline = [
            {
                '$lookup': {
                    'from': 'documents',
                    'localField': 'document_id',
                    'foreignField': '_id',
                    'as': 'document'
                }
            },
            {
                '$match': {
                    'document.user_id': user_id,
                    'deadlines': {'$exists': True, '$ne': []}
                }
            }
        ]
        
        deadlines_with_dates = []
        # Implementation will extract and parse deadline dates
        return deadlines_with_dates
    
    def to_dict(self):
        """Convert clause to dictionary"""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'simplified_text': self.simplified_text,
            'clause_type': self.clause_type,
            'section_number': self.section_number,
            'risk_level': self.risk_level,
            'deadlines': self.deadlines,
            'obligations': self.obligations,
            'advice': self.advice,
            'created_at': self.created_at
        }