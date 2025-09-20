import google.generativeai as genai
from backend.models.document import Document
from backend.models.clause import Clause
from bson import ObjectId

class QAAgent:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def answer_question(self, question, user_id, document_id=None, conversation_id=None):
        """Answer questions about documents using stored knowledge and conversation history"""
        try:
            print(f"Answering question: {question}")
            print(f"User ID: {user_id}, Document ID: {document_id}, Conversation ID: {conversation_id}")
            
            # Import here to avoid circular imports
            from backend.models.conversation import Conversation
            
            # Get or create conversation
            if conversation_id:
                conversation = Conversation.find_by_id(conversation_id)
            else:
                conversation = Conversation.find_by_user_and_document(user_id, document_id)
                if not conversation:
                    conversation = Conversation(user_id=user_id, document_id=document_id)
                    conversation.save()
            
            # Add user message to conversation
            conversation.add_message('user', question)
            
            # Get relevant context
            context = self._get_relevant_context(question, user_id, document_id)
            
            if not context or not context.get('documents'):
                response = {
                    'answer': "I don't have any documents to reference for this question. Please upload a document first and ensure it has been processed.",
                    'confidence': 0.0,
                    'sources': [],
                    'conversation_id': conversation.id
                }
            else:
                # Get conversation history for context
                conversation_history = conversation.get_conversation_history(max_messages=6)  # Last 3 Q&A pairs
                
                print(f"Found context with {len(context['documents'])} documents and {len(context.get('clauses', []))} clauses")
                
                # Generate answer using AI with conversation history
                answer_data = self._generate_answer_with_history(question, context, conversation_history)
                answer_data['conversation_id'] = conversation.id
                
                # Add assistant response to conversation
                conversation.add_message('assistant', answer_data['answer'])
                
                response = answer_data
            
            return response
        
        except Exception as e:
            print(f"QA Error: {e}")
            return {
                'answer': f"I encountered an error while processing your question: {str(e)}",
                'confidence': 0.0,
                'sources': [],
                'conversation_id': None
            }
    def _generate_answer_with_history(self, question, context, conversation_history):
        """Generate an answer using AI with conversation history"""
        try:
            # Build context string for the AI
            context_str = self._build_context_string(context)
            
            if not context_str.strip():
                return {
                    'answer': "I don't have enough information about your documents to answer this question. Please ensure your documents have been processed successfully.",
                    'confidence': 0.1,
                    'sources': []
                }
            
            # Include conversation history in the prompt
            prompt = f"""
            You are a helpful legal document assistant. Answer the user's question based on the provided document context and previous conversation.
            
            Rules:
            1. Only answer based on the information in the provided documents
            2. Be clear and direct in your response
            3. Reference previous conversation when relevant
            4. If the documents don't contain relevant information, say so
            5. Cite specific sections when possible
            6. Explain any legal terms in simple language
            7. If there are potential risks or important considerations, mention them
            
            Previous Conversation:
            {conversation_history}
            
            Current Question: {question}
            
            Document Context:
            {context_str}
            
            Answer:
            """
            
            response = self.model.generate_content(prompt)
            answer_text = response.text.strip()
            
            # Calculate confidence based on context relevance
            confidence = self._calculate_confidence(context, question)
            
            # Extract sources referenced in the answer
            sources = self._extract_sources(context['relevant_clauses'], answer_text)
            
            return {
                'answer': answer_text,
                'confidence': confidence,
                'sources': sources,
                'context_used': len(context['relevant_clauses'])
            }
        
        except Exception as e:
            print(f"Answer generation with history failed: {e}")
            return {
                'answer': "I encountered an error generating the answer. Please try rephrasing your question.",
                'confidence': 0.0,
                'sources': []
            }
        
    def _get_relevant_context(self, question, user_id, document_id=None):
        """Get relevant document context for the question"""
        context = {
            'documents': [],
            'clauses': [],
            'question_keywords': self._extract_keywords(question)
        }
        
        try:
            if document_id:
                # Get document
                document = Document.find_by_id(document_id)
                
                if document and str(document.user_id) == str(user_id):
                    print(f"Found document: {document.filename}")
                    context['documents'].append(document)
                    
                    # Try to get clauses - test both ways
                    clauses = Clause.find_by_document_id(document_id)
                    print(f"Found {len(clauses)} clauses with string ID")
                    
                    # If no clauses found, try with document.id
                    if not clauses:
                        clauses = Clause.find_by_document_id(document.id)
                        print(f"Found {len(clauses)} clauses with document.id")
                    
                    context['clauses'].extend(clauses) 
            else:
                # Get all user documents
                documents = Document.find_by_user_id(user_id, limit=5)
                print(f"Found {len(documents)} documents for user")
                context['documents'].extend(documents)
                
                # Get clauses from all documents
                for doc in documents:
                    if doc.status == 'completed':  # Only get clauses from completed documents
                        doc_clauses = Clause.find_by_document_id(doc.id)
                        context['clauses'].extend(doc_clauses)
            
            # Filter clauses by relevance
            if context['clauses']:
                context['relevant_clauses'] = self._filter_relevant_clauses(
                    context['clauses'], 
                    context['question_keywords']
                )
                print(f"Found {len(context['relevant_clauses'])} relevant clauses")
            else:
                context['relevant_clauses'] = []
                print("No clauses found")
            
            return context
        
        except Exception as e:
            print(f"Error getting context: {str(e)}")
            return None
    
    def _extract_keywords(self, question):
        """Extract key terms from the question"""
        question_lower = question.lower()
        
        # Common legal/contract keywords
        legal_keywords = [
            'termination', 'cancel', 'end', 'break',
            'payment', 'fee', 'cost', 'money', 'price',
            'deadline', 'date', 'time', 'when', 'duration',
            'obligation', 'must', 'required', 'responsible',
            'penalty', 'fine', 'consequence', 'breach',
            'right', 'entitled', 'benefit', 'privilege',
            'liability', 'risk', 'damages', 'insurance',
            'confidential', 'private', 'disclosure',
            'renewal', 'extension', 'automatic',
            'dispute', 'arbitration', 'court', 'legal'
        ]
        
        found_keywords = []
        for keyword in legal_keywords:
            if keyword in question_lower:
                found_keywords.append(keyword)
        
        # Also extract potential entity names (simple approach)
        words = question.split()
        for word in words:
            if len(word) > 3 and word.lower() not in ['what', 'when', 'where', 'how', 'why', 'who', 'this', 'that', 'with']:
                found_keywords.append(word.lower())
        
        return found_keywords
    
    def _filter_relevant_clauses(self, clauses, keywords):
        """Filter clauses that are most relevant to the question"""
        relevant_clauses = []
        
        for clause in clauses:
            relevance_score = 0
            
            # Check both original and simplified text
            clause_text = (clause.simplified_text + " " + clause.original_text).lower()
            
            # Score based on keyword matches
            for keyword in keywords:
                if keyword in clause_text:
                    relevance_score += 1
            
            # Boost score for certain clause types
            important_types = ['obligation', 'deadline', 'penalty', 'risk']
            if clause.clause_type in important_types:
                relevance_score += 2
            
            if relevance_score > 0:
                clause_data = clause.to_dict()
                clause_data['relevance_score'] = relevance_score
                relevant_clauses.append(clause_data)
        
        # Sort by relevance score and return top matches
        relevant_clauses.sort(key=lambda x: x['relevance_score'], reverse=True)
        return relevant_clauses[:10]  # Limit to top 10 most relevant
    
    def _generate_answer(self, question, context):
        """Generate an answer using AI with the provided context"""
        try:
            # Build context string for the AI
            context_str = self._build_context_string(context)
            
            if not context_str.strip():
                return {
                    'answer': "I don't have enough information about your documents to answer this question. Please ensure your documents have been processed successfully.",
                    'confidence': 0.1,
                    'sources': []
                }
            
            prompt = f"""
            You are a helpful legal document assistant. Answer the user's question based on the provided document context.
            
            Rules:
            1. Only answer based on the information in the provided documents
            2. Be clear and direct in your response
            3. If the documents don't contain relevant information, say so
            4. Cite specific sections when possible
            5. Explain any legal terms in simple language
            6. If there are potential risks or important considerations, mention them
            
            Question: {question}
            
            Document Context:
            {context_str}
            
            Answer:
            """
            
            response = self.model.generate_content(prompt)
            answer_text = response.text.strip()
            
            # Calculate confidence based on context relevance
            confidence = self._calculate_confidence(context, question)
            
            # Extract sources referenced in the answer
            sources = self._extract_sources(context['relevant_clauses'], answer_text)
            
            return {
                'answer': answer_text,
                'confidence': confidence,
                'sources': sources,
                'context_used': len(context['relevant_clauses'])
            }
        
        except Exception as e:
            print(f"Answer generation failed: {e}")
            return {
                'answer': "I encountered an error generating the answer. Please try rephrasing your question.",
                'confidence': 0.0,
                'sources': []
            }
    
    def _build_context_string(self, context):
        """Build a context string from documents and clauses"""
        context_parts = []
        
        # Add document information
        for doc in context['documents']:
            context_parts.append(f"Document: {doc.filename} ({doc.document_type})")
            if doc.summary:
                context_parts.append(f"Summary: {doc.summary}")
        
        # Add relevant clauses
        for clause in context['relevant_clauses']:
            context_parts.append(f"\nSection {clause['section_number']} ({clause['clause_type']}):")
            context_parts.append(clause['simplified_text'])
            
            if clause.get('advice'):
                context_parts.append(f"Advice: {clause['advice']}")
        
        return "\n".join(context_parts)
    
    def _calculate_confidence(self, context, question):
        """Calculate confidence score for the answer"""
        base_confidence = 0.5
        
        # Increase confidence based on relevant clauses found
        num_relevant = len(context['relevant_clauses'])
        if num_relevant > 0:
            base_confidence += min(0.3, num_relevant * 0.1)
        
        # Increase confidence if question keywords match context
        keyword_matches = 0
        context_text = self._build_context_string(context).lower()
        for keyword in context['question_keywords']:
            if keyword in context_text:
                keyword_matches += 1
        
        if keyword_matches > 0:
            base_confidence += min(0.2, keyword_matches * 0.05)
        
        return min(1.0, base_confidence)
    
    def _extract_sources(self, relevant_clauses, answer_text):
        """Extract which clauses were likely used as sources"""
        sources = []
        
        for clause in relevant_clauses[:5]:  # Check top 5 relevant clauses
            # Simple heuristic: if clause text appears in answer or vice versa
            clause_words = set(clause['simplified_text'].lower().split())
            answer_words = set(answer_text.lower().split())
            
            # Calculate word overlap
            overlap = len(clause_words.intersection(answer_words))
            overlap_ratio = overlap / max(len(clause_words), 1)
            
            if overlap_ratio > 0.1:  # Threshold for considering it a source
                sources.append({
                    'section': clause['section_number'],
                    'type': clause['clause_type'],
                    'text_preview': clause['simplified_text'][:150] + "...",
                    'document_id': clause['document_id']
                })
        
        return sources
    
    def get_suggested_questions(self, user_id, document_id=None):
        """Generate suggested questions based on document content"""
        try:
            print(f"Getting suggested questions for user {user_id}, document {document_id}")
            
            if document_id:
                clauses = Clause.find_by_document_id(document_id)
                print(f"Found {len(clauses)} clauses for document")
            else:
                # Get clauses from recent documents
                documents = Document.find_by_user_id(user_id, limit=3)
                clauses = []
                for doc in documents:
                    if doc.status == 'completed':
                        doc_clauses = Clause.find_by_document_id(doc.id)
                        clauses.extend(doc_clauses)
                print(f"Found {len(clauses)} total clauses from user documents")
            
            if not clauses:
                return [
                    "What are the key terms of this agreement?",
                    "What are my main obligations?", 
                    "Are there any important deadlines?",
                    "What risks should I be aware of?"
                ]
            
            # Generate questions based on clause types
            suggestions = []
            
            # Check for different clause types and suggest relevant questions
            clause_types = set(clause.clause_type for clause in clauses)
            
            if 'deadline' in clause_types:
                suggestions.append("What are the important deadlines in this document?")
                suggestions.append("When do I need to take action?")
            
            if 'penalty' in clause_types:
                suggestions.append("What penalties could I face if I don't comply?")
                suggestions.append("What happens if I break this agreement?")
            
            if 'obligation' in clause_types:
                suggestions.append("What are my main obligations under this agreement?")
                suggestions.append("What do I need to do to comply with this document?")
            
            # Check for termination-related content
            has_termination = any('termination' in clause.simplified_text.lower() for clause in clauses)
            if has_termination:
                suggestions.append("How can this agreement be terminated?")
                suggestions.append("Can I cancel this agreement early?")
            
            # Always include these general questions
            suggestions.extend([
                "What are the biggest risks in this document?",
                "What should I be most concerned about?",
                "Can you summarize the key points?"
            ])
            
            # Remove duplicates and return up to 6 suggestions
            unique_suggestions = list(dict.fromkeys(suggestions))
            return unique_suggestions[:6]
        
        except Exception as e:
            print(f"Error generating suggestions: {e}")
            return [
                "What are the key terms of this agreement?",
                "What are my main obligations?",
                "Are there any important deadlines?", 
                "What risks should I be aware of?"
            ]