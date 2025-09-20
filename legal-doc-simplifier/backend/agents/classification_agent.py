import google.generativeai as genai
import re

class ClauseClassificationAgent:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Define clause type categories
        self.clause_types = [
            'obligation',   # What you must do
            'right',       # What you're entitled to
            'risk',        # Potential problems or liability
            'penalty',     # Consequences for non-compliance
            'deadline',    # Time-sensitive requirements
            'general'      # Other informational clauses
        ]
    
    def classify_clauses(self, sections):
        """Classify each section/clause by type"""
        classified_clauses = []
        
        for section in sections:
            try:
                classification = self._classify_single_clause(section['text'])
                
                clause_data = {
                    'text': section['text'],
                    'section_number': section['section_number'],
                    'clause_type': classification['type'],
                    'confidence': classification['confidence'],
                    'risk_level': classification['risk_level'],
                    'key_phrases': classification['key_phrases'],
                    'deadlines_found': classification['deadlines'],
                    'obligations_found': classification['obligations']
                }
                
                classified_clauses.append(clause_data)
            
            except Exception as e:
                # Fallback classification
                fallback_classification = self._fallback_classify(section['text'])
                clause_data = {
                    'text': section['text'],
                    'section_number': section['section_number'],
                    'clause_type': fallback_classification,
                    'confidence': 0.5,
                    'risk_level': 'medium',
                    'key_phrases': [],
                    'deadlines_found': [],
                    'obligations_found': []
                }
                classified_clauses.append(clause_data)
        
        return classified_clauses
    
    def _classify_single_clause(self, clause_text):
        """Classify a single clause using AI"""
        prompt = f"""
        Analyze this legal clause and classify it into one of these categories:
        - obligation: Things the reader must do or comply with
        - right: Things the reader is entitled to or benefits they receive
        - risk: Potential problems, liability, or negative consequences
        - penalty: Specific punishments or fees for non-compliance
        - deadline: Time-sensitive requirements or important dates
        - general: General information, definitions, or background
        
        Clause text: {clause_text}
        
        Also assess:
        1. Risk level (low/medium/high)
        2. Key phrases that indicate the classification
        3. Any specific deadlines mentioned
        4. Any obligations mentioned
        
        Respond in this exact format:
        TYPE: [category]
        RISK_LEVEL: [low/medium/high]
        KEY_PHRASES: [comma-separated list]
        DEADLINES: [any dates or time periods found]
        OBLIGATIONS: [any specific things that must be done]
        CONFIDENCE: [0.0-1.0]
        """
        
        response = self.model.generate_content(prompt)
        return self._parse_classification_response(response.text)
    
    def _parse_classification_response(self, response_text):
        """Parse the structured response from the AI model"""
        try:
            lines = response_text.strip().split('\n')
            result = {
                'type': 'general',
                'risk_level': 'low',
                'key_phrases': [],
                'deadlines': [],
                'obligations': [],
                'confidence': 0.7
            }
            
            for line in lines:
                if line.startswith('TYPE:'):
                    result['type'] = line.split(':', 1)[1].strip().lower()
                elif line.startswith('RISK_LEVEL:'):
                    result['risk_level'] = line.split(':', 1)[1].strip().lower()
                elif line.startswith('KEY_PHRASES:'):
                    phrases = line.split(':', 1)[1].strip()
                    result['key_phrases'] = [p.strip() for p in phrases.split(',') if p.strip()]
                elif line.startswith('DEADLINES:'):
                    deadlines = line.split(':', 1)[1].strip()
                    result['deadlines'] = [d.strip() for d in deadlines.split(',') if d.strip()]
                elif line.startswith('OBLIGATIONS:'):
                    obligations = line.split(':', 1)[1].strip()
                    result['obligations'] = [o.strip() for o in obligations.split(',') if o.strip()]
                elif line.startswith('CONFIDENCE:'):
                    try:
                        result['confidence'] = float(line.split(':', 1)[1].strip())
                    except ValueError:
                        result['confidence'] = 0.7
            
            # Validate clause type
            if result['type'] not in self.clause_types:
                result['type'] = 'general'
            
            return result
        
        except Exception as e:
            return {
                'type': 'general',
                'risk_level': 'medium',
                'key_phrases': [],
                'deadlines': [],
                'obligations': [],
                'confidence': 0.5
            }
    
    def _fallback_classify(self, clause_text):
        """Fallback classification using keyword matching"""
        clause_lower = clause_text.lower()
        
        # Define keyword patterns for each clause type
        patterns = {
            'obligation': [
                r'\b(must|shall|required|obligated|responsible|duty|covenant)\b',
                r'\b(agree to|undertake|commit|promise)\b'
            ],
            'right': [
                r'\b(entitled|right|benefit|receive|privilege)\b',
                r'\b(may|permitted|allowed|can)\b'
            ],
            'risk': [
                r'\b(liable|responsibility|risk|damages|loss|penalty)\b',
                r'\b(breach|violation|default|failure)\b'
            ],
            'penalty': [
                r'\b(fine|penalty|fee|charge|forfeit)\b',
                r'\b(terminate|cancel|suspend)\b'
            ],
            'deadline': [
                r'\b(within|before|after|by|until|deadline)\b',
                r'\b\d+\s+(days?|weeks?|months?|years?)\b',
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b'
            ]
        }
        
        # Score each type
        scores = {}
        for clause_type, type_patterns in patterns.items():
            score = 0
            for pattern in type_patterns:
                matches = len(re.findall(pattern, clause_lower))
                score += matches
            scores[clause_type] = score
        
        # Return the highest scoring type or 'general' if no matches
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return 'general'
    
    def get_clause_statistics(self, classified_clauses):
        """Generate statistics about clause classifications"""
        total_clauses = len(classified_clauses)
        type_counts = {}
        risk_counts = {'low': 0, 'medium': 0, 'high': 0}
        
        for clause in classified_clauses:
            # Count by type
            clause_type = clause['clause_type']
            type_counts[clause_type] = type_counts.get(clause_type, 0) + 1
            
            # Count by risk level
            risk_level = clause['risk_level']
            if risk_level in risk_counts:
                risk_counts[risk_level] += 1
        
        return {
            'total_clauses': total_clauses,
            'type_distribution': type_counts,
            'risk_distribution': risk_counts,
            'high_risk_clauses': [c for c in classified_clauses if c['risk_level'] == 'high'],
            'deadline_clauses': [c for c in classified_clauses if c['clause_type'] == 'deadline' or c['deadlines_found']]
        }