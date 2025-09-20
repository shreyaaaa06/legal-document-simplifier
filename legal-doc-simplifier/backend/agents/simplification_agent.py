import google.generativeai as genai

class SimplificationAgent:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def simplify_clauses(self, classified_clauses, simplification_level='general'):
        """Simplify all clauses to plain English"""
        simplified_clauses = []
        
        for clause in classified_clauses:
            try:
                simplified_text = self._simplify_single_clause(
                    clause['text'], 
                    clause['clause_type'],
                    simplification_level
                )
                
                clause_data = clause.copy()
                clause_data['simplified_text'] = simplified_text
                clause_data['simplification_level'] = simplification_level
                
                simplified_clauses.append(clause_data)
            
            except Exception as e:
                # Keep original text if simplification fails
                clause_data = clause.copy()
                clause_data['simplified_text'] = clause['text']
                clause_data['simplification_level'] = 'original'
                simplified_clauses.append(clause_data)
        
        return simplified_clauses
    
    def _simplify_single_clause(self, clause_text, clause_type, level):
        """Simplify a single clause based on the target audience level"""
        
        level_instructions = {
            'general': """
                Rewrite this in simple, everyday language that anyone can understand.
                Use short sentences and common words. Avoid legal jargon completely.
                Make it sound like you're explaining to a friend.
            """,
            'student': """
                Rewrite this for a college student level. Use clear language but you can
                include some technical terms if you explain them. Make it educational.
            """,
            'professional': """
                Rewrite this for a business professional. Keep some technical terms
                but make the meaning and implications very clear. Focus on practical impact.
            """,
            'lawyer': """
                Rewrite this to be clearer while maintaining legal precision.
                Simplify structure and language but don't lose important legal nuances.
            """
        }
        
        clause_context = {
            'obligation': "This clause describes something you must do or comply with.",
            'right': "This clause describes something you're entitled to or a benefit you receive.",
            'risk': "This clause describes potential problems or liability you should be aware of.",
            'penalty': "This clause describes consequences if you don't comply with the agreement.",
            'deadline': "This clause contains important dates or time requirements.",
            'general': "This clause provides general information about the agreement."
        }
        
        prompt = f"""
        {level_instructions.get(level, level_instructions['general'])}
        
        Context: {clause_context.get(clause_type, clause_context['general'])}
        
        Original legal text:
        {clause_text}
        
        Simplified version:
        """
        
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def generate_document_summary(self, simplified_clauses, document_type):
        """Generate an overall document summary"""
        try:
            # Group clauses by type for summary
            clause_groups = {}
            for clause in simplified_clauses:
                clause_type = clause['clause_type']
                if clause_type not in clause_groups:
                    clause_groups[clause_type] = []
                clause_groups[clause_type].append(clause['simplified_text'])
            
            # Create summary prompt
            summary_content = ""
            for clause_type, clauses in clause_groups.items():
                summary_content += f"\n{clause_type.upper()} CLAUSES:\n"
                for i, clause in enumerate(clauses[:3], 1):  # Limit to first 3 per type
                    summary_content += f"{i}. {clause[:200]}...\n"
            
            prompt = f"""
            Create a comprehensive but concise summary of this {document_type}.
            
            Focus on:
            1. What this document is about
            2. Key obligations and requirements
            3. Important rights and benefits
            4. Major risks or concerns
            5. Critical deadlines
            
            Document content:
            {summary_content}
            
            Write the summary in plain English, as if explaining to someone who has never seen this document before.
            Make it practical and actionable.
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
        
        except Exception as e:
            return f"Summary of {document_type}: This document contains {len(simplified_clauses)} clauses covering various legal terms and conditions."
    
    def create_quick_highlights(self, simplified_clauses):
        """Create quick highlights of the most important points"""
        try:
            # Get high-risk and deadline clauses
            important_clauses = []
            
            for clause in simplified_clauses:
                if (clause['risk_level'] == 'high' or 
                    clause['clause_type'] in ['penalty', 'deadline', 'risk'] or
                    clause.get('deadlines_found')):
                    important_clauses.append(clause)
            
            if not important_clauses:
                # If no high-priority clauses, take first few clauses
                important_clauses = simplified_clauses[:3]
            
            highlights = []
            for clause in important_clauses[:5]:  # Limit to 5 highlights
                highlight = {
                    'type': clause['clause_type'],
                    'risk_level': clause['risk_level'],
                    'text': clause['simplified_text'][:300] + "..." if len(clause['simplified_text']) > 300 else clause['simplified_text'],
                    'section': clause['section_number']
                }
                highlights.append(highlight)
            
            return highlights
        
        except Exception as e:
            return []
    
    def generate_action_items(self, simplified_clauses):
        """Generate actionable items from the document"""
        try:
            # Focus on obligations and deadlines
            action_clauses = [
                clause for clause in simplified_clauses 
                if clause['clause_type'] in ['obligation', 'deadline'] or clause.get('obligations_found')
            ]
            
            if not action_clauses:
                return []
            
            action_text = ""
            for clause in action_clauses:
                action_text += f"- {clause['simplified_text']}\n"
            
            prompt = f"""
            Based on these legal clauses, create a clear action item checklist for someone who signed this document.
            
            Clauses:
            {action_text}
            
            Create specific, actionable items in this format:
            • [Action item]
            • [Action item]
            
            Focus on what the person actually needs to DO, not just what they should know.
            Include any deadlines or time requirements.
            """
            
            response = self.model.generate_content(prompt)
            action_items = []
            
            for line in response.text.split('\n'):
                line = line.strip()
                if line.startswith('•') or line.startswith('-'):
                    action_items.append(line[1:].strip())
            
            return action_items
        
        except Exception as e:
            return []