import re
from datetime import datetime
import google.generativeai as genai

class PreprocessingAgent:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def preprocess_document(self, text, filename):
        """Main preprocessing pipeline"""
        try:
            print(f"Starting preprocessing for {filename}")
            
            # Clean and normalize text
            cleaned_text = self._clean_text(text)
            print(f"Text cleaned, length: {len(cleaned_text)}")
            
            # Split into meaningful sections (FIXED - no more duplicates)
            sections = self._split_into_meaningful_sections(cleaned_text)
            print(f"Split into {len(sections)} sections")
            
            # Extract entities and metadata
            entities = self._extract_entities(cleaned_text)
            
            # Determine document type
            doc_type = self._classify_document_type(cleaned_text, filename)
            print(f"Document type: {doc_type}")
            
            return {
                'cleaned_text': cleaned_text,
                'sections': sections,
                'entities': entities,
                'document_type': doc_type,
                'total_sections': len(sections)
            }
        
        except Exception as e:
            print(f"Preprocessing failed: {e}")
            raise Exception(f"Preprocessing failed: {str(e)}")
    
    def _clean_text(self, text):
        """Clean and normalize document text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere with processing
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\"\'\/\&\%\$\@\#]', '', text)
        
        # Normalize line breaks
        text = re.sub(r'\r\n|\r|\n', '\n', text)
        
        return text.strip()
    
    def _split_into_meaningful_sections(self, text):
        """Split document into meaningful sections WITHOUT duplication"""
        # Split by common legal document patterns
        section_markers = [
            r'\n\s*\d+\.\s+',          # 1., 2., 3.
            r'\n\s*\([a-z]\)\s+',      # (a), (b), (c)
            r'\n\s*\(\d+\)\s+',        # (1), (2), (3)
            r'\n\s*[A-Z][A-Z\s]+:\s*', # TITLE CASE:
            r'\n\s*Article\s+\d+',      # Article 1, Article 2
            r'\n\s*Section\s+\d+',      # Section 1, Section 2
            r'\n\s*WHEREAS',            # Contract clauses
            r'\n\s*NOW THEREFORE',      # Contract clauses
            r'\n\s*\d+\s*\.\s*\d+',    # 1.1, 1.2, etc.
        ]
        
        # Create a combined pattern
        combined_pattern = '|'.join(f'({pattern})' for pattern in section_markers)
        
        # Split text by section markers
        parts = re.split(combined_pattern, text, flags=re.IGNORECASE)
        
        # Clean up and reconstruct sections
        sections = []
        current_section = ""
        
        for part in parts:
            if part is None or part.strip() == "":
                continue
                
            # If this looks like a section marker, start new section
            if re.match(combined_pattern, part, re.IGNORECASE):
                if current_section.strip():
                    sections.append(self._create_section_data(current_section.strip(), len(sections) + 1))
                current_section = part
            else:
                current_section += part
        
        # Add the last section
        if current_section.strip():
            sections.append(self._create_section_data(current_section.strip(), len(sections) + 1))
        
        # If no sections found, split by paragraphs
        if len(sections) <= 1:
            print("No section markers found, splitting by paragraphs")
            sections = self._split_by_paragraphs(text)
        
        # Remove very short or empty sections
        sections = [s for s in sections if len(s['text'].strip()) > 50]
        
        # Limit to reasonable number of sections (avoid too many tiny sections)
        if len(sections) > 20:
            sections = self._merge_small_sections(sections, max_sections=20)
        
        print(f"Final section count: {len(sections)}")
        return sections
    
    def _split_by_paragraphs(self, text):
        """Fallback: split by paragraphs"""
        paragraphs = text.split('\n\n')
        sections = []
        
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip() and len(paragraph.strip()) > 50:
                sections.append(self._create_section_data(paragraph.strip(), i + 1))
        
        return sections
    
    def _merge_small_sections(self, sections, max_sections=20):
        """Merge small sections to avoid too much fragmentation"""
        if len(sections) <= max_sections:
            return sections
        
        merged = []
        current_merged = {"text": "", "section_number": 1}
        target_length = len(sections) // max_sections + 1
        
        for i, section in enumerate(sections):
            current_merged["text"] += section["text"] + "\n\n"
            
            # Merge sections until we reach target length or end
            if (i + 1) % target_length == 0 or i == len(sections) - 1:
                current_merged["text"] = current_merged["text"].strip()
                current_merged["word_count"] = len(current_merged["text"].split())
                current_merged["has_marker"] = True  # Assume merged sections have markers
                merged.append(current_merged)
                
                current_merged = {
                    "text": "", 
                    "section_number": len(merged) + 1
                }
        
        return merged[:max_sections]
    
    def _create_section_data(self, text, section_number):
        """Create standardized section data"""
        return {
            'text': text.strip(),
            'section_number': section_number,
            'has_marker': True,  # We found this via markers
            'word_count': len(text.split())
        }
    
    def _extract_entities(self, text):
        """Extract key entities from document text"""
        entities = {
            'dates': [],
            'monetary_amounts': [],
            'parties': [],
            'deadlines': [],
            'obligations': [],
            'penalties': []
        }
        
        # Extract dates
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{2,4}\b',
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}\b'
        ]
        
        for pattern in date_patterns:
            entities['dates'].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Extract monetary amounts
        money_patterns = [
            r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
            r'\b\d+\s*dollars?\b',
            r'\b\d+\s*USD\b'
        ]
        
        for pattern in money_patterns:
            entities['monetary_amounts'].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Extract potential party names (simplified)
        party_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last names
            r'\b[A-Z][A-Z\s&]+(?:LLC|Inc|Corp|Corporation|Company|Ltd)\b'  # Company names
        ]
        
        for pattern in party_patterns:
            entities['parties'].extend(re.findall(pattern, text))
        
        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
    
    def _classify_document_type(self, text, filename):
        """Classify the type of legal document using AI"""
        try:
            prompt = f"""
            Analyze the following document text and filename to determine the document type.
            
            Filename: {filename}
            Text sample (first 1000 chars): {text[:1000]}
            
            Classify this document as one of the following types:
            - Employment Contract
            - Rental Agreement
            - Loan Agreement  
            - Privacy Policy
            - Terms of Service
            - Insurance Policy
            - Purchase Agreement
            - Service Agreement
            - Non-Disclosure Agreement
            - Other Legal Document
            
            Respond with only the document type, no explanation.
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
        
        except Exception as e:
            # Fallback to keyword-based classification
            return self._fallback_document_classification(text, filename)
    
    def _fallback_document_classification(self, text, filename):
        """Fallback document classification using keywords"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Define keywords for each document type
        classification_keywords = {
            'Employment Contract': ['employment', 'employee', 'employer', 'salary', 'wages', 'termination', 'job'],
            'Rental Agreement': ['rent', 'lease', 'tenant', 'landlord', 'property', 'premises', 'monthly'],
            'Loan Agreement': ['loan', 'borrow', 'lender', 'interest', 'payment', 'principal', 'debt'],
            'Privacy Policy': ['privacy', 'data', 'information', 'collect', 'cookies', 'personal'],
            'Terms of Service': ['terms', 'service', 'user', 'website', 'platform', 'agreement'],
            'Insurance Policy': ['insurance', 'coverage', 'premium', 'claim', 'policy', 'insured'],
            'Purchase Agreement': ['purchase', 'sale', 'buyer', 'seller', 'goods', 'product'],
            'Service Agreement': ['service', 'provider', 'client', 'work', 'deliverable'],
            'Non-Disclosure Agreement': ['confidential', 'non-disclosure', 'nda', 'proprietary', 'secret']
        }
        
        # Score each document type
        scores = {}
        for doc_type, keywords in classification_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower or keyword in filename_lower)
            scores[doc_type] = score
        
        # Return the highest scoring type
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return 'Other Legal Document'
    def extract_deadline_dates(self, text, document_creation_date=None):
        """Extract and parse deadline dates from text"""
        try:
            prompt = f"""
            Extract specific deadline dates from this text. For each deadline found, provide:
            1. The exact deadline text
            2. The calculated date (if possible)
            3. The type of deadline (payment, renewal, termination, etc.)
            
            Text: {text}
            Document creation date: {document_creation_date or 'Unknown'}
            
            Format response as:
            DEADLINE: [text] | DATE: [YYYY-MM-DD or relative] | TYPE: [type]
            """
            
            response = self.model.generate_content(prompt)
            return self._parse_deadline_response(response.text)
            
        except Exception as e:
            return self._fallback_deadline_extraction(text)