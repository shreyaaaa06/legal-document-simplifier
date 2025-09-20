import google.generativeai as genai
from datetime import datetime, timedelta
import re

class RiskAnalysisAgent:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def analyze_document_risks(self, simplified_clauses, document_type):
        """Comprehensive risk analysis of the entire document"""
        try:
            risk_analysis = {
                'overall_risk_score': 0,
                'risk_categories': {},
                'high_risk_clauses': [],
                'deadlines': [],
                'financial_obligations': [],
                'termination_risks': [],
                'compliance_requirements': [],
                'recommendations': []
            }
            
            # Analyze each clause for risks
            for clause in simplified_clauses:
                clause_risks = self._analyze_clause_risks(clause)
                self._update_risk_analysis(risk_analysis, clause_risks, clause)
            
            # Generate overall risk score (0-100)
            risk_analysis['overall_risk_score'] = self._calculate_overall_risk_score(risk_analysis)
            
            # Generate recommendations
            risk_analysis['recommendations'] = self._generate_risk_recommendations(
                risk_analysis, document_type
            )
            
            return risk_analysis
        
        except Exception as e:
            return self._get_fallback_risk_analysis()
    
    def _analyze_clause_risks(self, clause):
        """Analyze risks in a single clause"""
        try:
            prompt = f"""
            Analyze this legal clause for potential risks and concerns:
            
            Clause Type: {clause['clause_type']}
            Risk Level: {clause['risk_level']}
            Text: {clause['simplified_text']}
            
            Identify:
            1. Specific risks or potential problems
            2. Financial implications or costs
            3. Deadlines or time-sensitive requirements
            4. Termination or cancellation conditions
            5. Compliance requirements
            6. Penalty or consequence severity
            
            Respond in this format:
            RISKS: [list specific risks]
            FINANCIAL: [any monetary implications]
            DEADLINES: [any time requirements]
            TERMINATION: [termination conditions]
            COMPLIANCE: [what must be complied with]
            SEVERITY: [low/medium/high/critical]
            """
            
            response = self.model.generate_content(prompt)
            return self._parse_risk_response(response.text)
        
        except Exception as e:
            return self._get_fallback_clause_risks(clause)
    
    def _parse_risk_response(self, response_text):
        """Parse the structured risk analysis response"""
        risks = {
            'risks': [],
            'financial': [],
            'deadlines': [],
            'termination': [],
            'compliance': [],
            'severity': 'low'
        }
        
        try:
            lines = response_text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('RISKS:'):
                    content = line.split(':', 1)[1].strip()
                    risks['risks'] = [r.strip() for r in content.split(',') if r.strip()]
                elif line.startswith('FINANCIAL:'):
                    content = line.split(':', 1)[1].strip()
                    risks['financial'] = [f.strip() for f in content.split(',') if f.strip()]
                elif line.startswith('DEADLINES:'):
                    content = line.split(':', 1)[1].strip()
                    risks['deadlines'] = [d.strip() for d in content.split(',') if d.strip()]
                elif line.startswith('TERMINATION:'):
                    content = line.split(':', 1)[1].strip()
                    risks['termination'] = [t.strip() for t in content.split(',') if t.strip()]
                elif line.startswith('COMPLIANCE:'):
                    content = line.split(':', 1)[1].strip()
                    risks['compliance'] = [c.strip() for c in content.split(',') if c.strip()]
                elif line.startswith('SEVERITY:'):
                    severity = line.split(':', 1)[1].strip().lower()
                    if severity in ['low', 'medium', 'high', 'critical']:
                        risks['severity'] = severity
            
            return risks
        
        except Exception as e:
            return risks
    
    def _update_risk_analysis(self, risk_analysis, clause_risks, clause):
        """Update the overall risk analysis with clause-specific risks"""
        # Update risk categories
        severity = clause_risks['severity']
        if severity not in risk_analysis['risk_categories']:
            risk_analysis['risk_categories'][severity] = 0
        risk_analysis['risk_categories'][severity] += 1
        
        # Add high-risk clauses
        if severity in ['high', 'critical']:
            risk_analysis['high_risk_clauses'].append({
                'section': clause['section_number'],
                'type': clause['clause_type'],
                'text': clause['simplified_text'],
                'risks': clause_risks['risks'],
                'severity': severity
            })
        
        # Add deadlines
        for deadline in clause_risks['deadlines']:
            if deadline and deadline.lower() != 'none':
                risk_analysis['deadlines'].append({
                    'section': clause['section_number'],
                    'deadline': deadline,
                    'context': clause['simplified_text'][:200] + "..."
                })
        
        # Add financial obligations
        for financial in clause_risks['financial']:
            if financial and financial.lower() != 'none':
                risk_analysis['financial_obligations'].append({
                    'section': clause['section_number'],
                    'obligation': financial,
                    'context': clause['simplified_text'][:200] + "..."
                })
        
        # Add termination risks
        for termination in clause_risks['termination']:
            if termination and termination.lower() != 'none':
                risk_analysis['termination_risks'].append({
                    'section': clause['section_number'],
                    'condition': termination,
                    'context': clause['simplified_text'][:200] + "..."
                })
        
        # Add compliance requirements
        for compliance in clause_risks['compliance']:
            if compliance and compliance.lower() != 'none':
                risk_analysis['compliance_requirements'].append({
                    'section': clause['section_number'],
                    'requirement': compliance,
                    'context': clause['simplified_text'][:200] + "..."
                })
    
    def _calculate_overall_risk_score(self, risk_analysis):
        """Calculate overall risk score from 0-100"""
        base_score = 30  # Base score
        
        # Add points for each risk category
        risk_weights = {
            'low': 5,
            'medium': 15,
            'high': 25,
            'critical': 40
        }
        
        for severity, count in risk_analysis['risk_categories'].items():
            base_score += risk_weights.get(severity, 0) * count
        
        # Additional points for specific risk types
        base_score += len(risk_analysis['financial_obligations']) * 5
        base_score += len(risk_analysis['termination_risks']) * 10
        base_score += len(risk_analysis['compliance_requirements']) * 5
        
        # Cap at 100
        return min(100, base_score)
    
    def _generate_risk_recommendations(self, risk_analysis, document_type):
        """Generate actionable recommendations based on risk analysis"""
        try:
            risk_summary = f"""
            Document Type: {document_type}
            Overall Risk Score: {risk_analysis['overall_risk_score']}/100
            High Risk Clauses: {len(risk_analysis['high_risk_clauses'])}
            Financial Obligations: {len(risk_analysis['financial_obligations'])}
            Deadlines: {len(risk_analysis['deadlines'])}
            Termination Risks: {len(risk_analysis['termination_risks'])}
            """
            
            prompt = f"""
            Based on this risk analysis, provide 3-5 specific, actionable recommendations 
            for someone who is considering signing or has signed this document.
            
            Risk Analysis:
            {risk_summary}
            
            Focus on:
            1. Most important actions to take
            2. Risks to mitigate or be aware of
            3. Professional advice that might be needed
            4. Timeline considerations
            5. Financial planning needs
            
            Make recommendations practical and specific.
            """
            
            response = self.model.generate_content(prompt)
            
            recommendations = []
            for line in response.text.split('\n'):
                line = line.strip()
                if line and (line.startswith('•') or line.startswith('-') or line[0].isdigit()):
                    # Clean up the recommendation text
                    clean_line = re.sub(r'^[•\-\d\.\)]+\s*', '', line)
                    if clean_line:
                        recommendations.append(clean_line)
            
            return recommendations[:5]  # Limit to 5 recommendations
        
        except Exception as e:
            return self._get_fallback_recommendations(risk_analysis['overall_risk_score'])
    
    def _get_fallback_clause_risks(self, clause):
        """Fallback risk analysis using keyword matching"""
        text = clause['simplified_text'].lower()
        
        risks = {
            'risks': [],
            'financial': [],
            'deadlines': [],
            'termination': [],
            'compliance': [],
            'severity': clause.get('risk_level', 'low')
        }
        
        # Simple keyword-based risk detection
        if any(word in text for word in ['penalty', 'fine', 'forfeit', 'damages']):
            risks['risks'].append('Potential financial penalties')
            risks['financial'].append('Penalty fees may apply')
        
        if any(word in text for word in ['terminate', 'cancel', 'void', 'breach']):
            risks['termination'].append('Agreement may be terminated')
        
        if any(word in text for word in ['within', 'days', 'deadline', 'before']):
            risks['deadlines'].append('Time-sensitive requirements')
        
        if any(word in text for word in ['must', 'shall', 'required', 'comply']):
            risks['compliance'].append('Compliance requirements')
        
        return risks
    
    def _get_fallback_risk_analysis(self):
        """Fallback risk analysis when AI analysis fails"""
        return {
            'overall_risk_score': 50,
            'risk_categories': {'medium': 1},
            'high_risk_clauses': [],
            'deadlines': [],
            'financial_obligations': [],
            'termination_risks': [],
            'compliance_requirements': [],
            'recommendations': [
                'Review the document carefully with legal counsel if needed',
                'Pay attention to any deadlines or time-sensitive requirements',
                'Understand your obligations and ensure you can meet them',
                'Keep records of all communications and compliance activities'
            ]
        }
    
    def _get_fallback_recommendations(self, risk_score):
        """Generate fallback recommendations based on risk score"""
        recommendations = [
            'Review all clauses carefully before signing'
        ]
        
        if risk_score > 70:
            recommendations.extend([
                'Consider seeking legal counsel due to high risk level',
                'Negotiate terms that seem unfavorable or unclear',
                'Ensure you have adequate insurance or financial resources'
            ])
        elif risk_score > 50:
            recommendations.extend([
                'Pay close attention to obligations and deadlines',
                'Consider professional advice for complex terms'
            ])
        else:
            recommendations.extend([
                'Ensure you understand all requirements',
                'Keep organized records of the agreement'
            ])
        
        return recommendations
    
    def extract_critical_dates(self, simplified_clauses):
        """Extract and parse critical dates and deadlines"""
        critical_dates = []
        
        for clause in simplified_clauses:
            dates = self._find_dates_in_text(clause['simplified_text'])
            
            for date_info in dates:
                critical_dates.append({
                    'section': clause['section_number'],
                    'date': date_info['date'],
                    'type': date_info['type'],
                    'description': date_info['description'],
                    'urgency': self._calculate_date_urgency(date_info['date']),
                    'context': clause['simplified_text'][:200] + "..."
                })
        
        # Sort by urgency and date
        critical_dates.sort(key=lambda x: (x['urgency'], x['date'] if x['date'] else datetime.max))
        
        return critical_dates
    
    def _find_dates_in_text(self, text):
        """Find and parse dates in text"""
        dates = []
        
        # Common date patterns
        date_patterns = [
            (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', 'specific_date'),
            (r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{2,4})\b', 'specific_date'),
            (r'\bwithin\s+(\d+)\s+(days?|weeks?|months?|years?)\b', 'relative_deadline'),
            (r'\b(\d+)\s+(days?|weeks?|months?|years?)\s+(before|after|from)\b', 'relative_deadline'),
        ]
        
        for pattern, date_type in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dates.append({
                    'date': self._parse_date_match(match, date_type),
                    'type': date_type,
                    'description': match.group(0),
                    'full_context': text
                })
        
        return dates
    
    def _parse_date_match(self, match, date_type):
        """Parse a date match into a datetime object"""
        try:
            if date_type == 'specific_date':
                # Try to parse the specific date
                date_str = match.group(0)
                # This would need more sophisticated date parsing
                return None  # Placeholder
            elif date_type == 'relative_deadline':
                # Calculate relative date from today
                number = int(match.group(1))
                unit = match.group(2).lower()
                
                if 'day' in unit:
                    return datetime.now() + timedelta(days=number)
                elif 'week' in unit:
                    return datetime.now() + timedelta(weeks=number)
                elif 'month' in unit:
                    return datetime.now() + timedelta(days=number*30)  # Approximate
                elif 'year' in unit:
                    return datetime.now() + timedelta(days=number*365)  # Approximate
            
            return None
        
        except Exception:
            return None
    
    def _calculate_date_urgency(self, date):
        """Calculate urgency level for a date"""
        if not date:
            return 3  # Medium urgency if date can't be parsed
        
        days_until = (date - datetime.now()).days
        
        if days_until < 0:
            return 1  # Past due - highest urgency
        elif days_until <= 7:
            return 2  # Within a week - high urgency
        elif days_until <= 30:
            return 3  # Within a month - medium urgency
        elif days_until <= 90:
            return 4  # Within 3 months - low urgency
        else:
            return 5  # More than 3 months - lowest urgency