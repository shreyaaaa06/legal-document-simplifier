from datetime import datetime
from bson import ObjectId
from backend.config.database import db_instance

class Conversation:
    def __init__(self, user_id, document_id=None, messages=None, _id=None, created_at=None):
        self.id = str(_id) if _id else None
        self.user_id = user_id
        self.document_id = document_id
        self.messages = messages or []  # List of {"role": "user/assistant", "content": "...", "timestamp": "..."}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def save(self):
        """Save conversation to database"""
        db = db_instance.get_db()
        conversation_data = {
            'user_id': self.user_id,
            'document_id': self.document_id,
            'messages': self.messages,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        if self.id:
            # Update existing conversation
            db.conversations.update_one(
                {'_id': ObjectId(self.id)},
                {'$set': conversation_data}
            )
        else:
            # Create new conversation
            result = db.conversations.insert_one(conversation_data)
            self.id = str(result.inserted_id)
        
        return self
    
    def add_message(self, role, content):
        """Add a message to the conversation"""
        message = {
            'role': role,  # 'user' or 'assistant'
            'content': content,
            'timestamp': datetime.utcnow()
        }
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return self.save()
    
    @staticmethod
    def find_by_user_and_document(user_id, document_id=None, limit=1):
        """Find conversation by user and document"""
        db = db_instance.get_db()
        
        query = {'user_id': user_id}
        if document_id:
            query['document_id'] = document_id
        else:
            query['document_id'] = None
        
        conversations = []
        cursor = db.conversations.find(query).sort('updated_at', -1)
        
        if limit:
            cursor = cursor.limit(limit)
        
        for conv_data in cursor:
            conversations.append(Conversation(
                user_id=conv_data['user_id'],
                document_id=conv_data.get('document_id'),
                messages=conv_data.get('messages', []),
                _id=conv_data['_id'],
                created_at=conv_data.get('created_at')
            ))
        
        return conversations[0] if conversations and limit == 1 else conversations
    
    @staticmethod
    def find_by_id(conversation_id):
        """Find conversation by ID"""
        db = db_instance.get_db()
        conv_data = db.conversations.find_one({'_id': ObjectId(conversation_id)})
        
        if conv_data:
            return Conversation(
                user_id=conv_data['user_id'],
                document_id=conv_data.get('document_id'),
                messages=conv_data.get('messages', []),
                _id=conv_data['_id'],
                created_at=conv_data.get('created_at')
            )
        return None
    
    def get_conversation_history(self, max_messages=10):
        """Get recent conversation history formatted for AI"""
        recent_messages = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        
        history = []
        for msg in recent_messages:
            history.append(f"{msg['role'].title()}: {msg['content']}")
        
        return "\n".join(history)
    
    def to_dict(self):
        """Convert conversation to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'document_id': self.document_id,
            'messages': self.messages,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }