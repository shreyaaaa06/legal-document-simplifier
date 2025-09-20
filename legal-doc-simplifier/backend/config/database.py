import os
from pymongo import MongoClient
from flask import current_app

class Database:
    def __init__(self):
        self.client = None
        self.db = None
    
    def initialize(self, app):
        """Initialize database connection"""
        
        self.client = MongoClient(app.config['MONGODB_URI'])
        self.db = self.client.legal_doc_simplifier
        
        # Create indexes for better performance
        self.db.users.create_index("email", unique=True)
        self.db.documents.create_index([("user_id", 1), ("created_at", -1)])
        self.db.conversations.create_index([("user_id", 1), ("document_id", 1), ("updated_at", -1)])
        # In the initialize method, add:
        self.db.clauses.create_index([("document_id", 1), ("clause_type", 1)])
    
    def get_db(self):
        """Get database instance"""
        return self.db
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()

# Global database instance
db_instance = Database()