# Legal Document Simplifier

A web-based AI system that transforms complex legal documents into clear, accessible explanations using multi-agent AI processing. The system analyzes risks, obligations, deadlines, and provides interactive Q&A capabilities with document memory.

## Features

### Core Functionality
- **Document Upload & Processing**: Support for PDF, DOCX, and scanned images with OCR
- **Multi-Agent AI Processing**: Automated clause classification, simplification, and risk analysis
- **Interactive Q&A**: Ask questions about any document or across all your documents
- **Dashboard Analytics**: Visual overview of deadlines, risks, and obligations
- **Document Memory**: Full history and searchable archive of all processed documents

### AI Agents
1. **Preprocessing Agent**: Extracts text, entities, dates, and structures documents
2. **Classification Agent**: Labels clauses as Obligation, Right, Risk, Penalty, or Deadline
3. **Simplification Agent**: Converts legal jargon into plain English
4. **Risk Analysis Agent**: Identifies potential risks and generates actionable advice
5. **Q&A Agent**: Provides intelligent responses using document knowledge base

### User Features
- **Secure Authentication**: User registration and login system
- **Visual Document Analysis**: Color-coded clause types and risk levels
- **Calendar View**: Interactive timeline for important deadlines
- **Chat History**: Track all your document conversations
- **Multi-level Summaries**: Tailored explanations for different user types

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **AI/ML**: Google Gemini API
- **Database**: MongoDB
- **OCR**: PyTesseract for scanned documents
- **Authentication**: Flask-Login

## Project Structure

```
legal-doc-simplifier/
├── backend/
│   ├── agents/
│   │   ├── preprocessing_agent.py
│   │   ├── classification_agent.py
│   │   ├── simplification_agent.py
│   │   ├── risk_analysis_agent.py
│   │   └── qa_agent.py
│   ├── models/
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── clause.py
│   │   └── conversation.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── documents.py
│   │   └── agents.py
│   ├── utils/
│   │   ├── ocr.py
│   │   ├── file_handler.py
│   │   └── auth_middleware.py
│   ├── config/
│   │   └── database.py
│   └── app.py
├── frontend/
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/main.js
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── upload.html
│   │   ├── document_analysis.html
│   │   └── chat_history.html
│   └── uploads/
└── .env
```

## Installation

### Prerequisites
- Python 3.8+
- MongoDB Atlas Account (free tier available)
- Tesseract OCR
- Google Gemini API Key

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd legal-doc-simplifier
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Install Tesseract OCR**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

4. **Set up MongoDB Atlas (Cloud)**
   - Create account at [MongoDB Atlas](https://www.mongodb.com/atlas)
   - Create a new cluster (free tier available)
   - Create a database user
   - Add your IP address to whitelist
   - Get your connection string from "Connect" button

5. **Configure environment variables**
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/legal_doc_simplifier?retryWrites=true&w=majority
GOOGLE_API_KEY=your-google-gemini-api-key
UPLOAD_FOLDER=frontend/uploads
MAX_CONTENT_LENGTH=16777216
FLASK_ENV=development
PORT=5000
```
*Replace the MONGODB_URI with your actual MongoDB Atlas connection string*

6. **Create upload directory**
```bash
mkdir -p frontend/uploads
```

## Usage

1. **Start the application**
```bash
python backend/app.py
```

2. **Open your browser**
Navigate to `http://localhost:5000`

3. **Register/Login**
Create a new account or login with existing credentials

4. **Upload Documents**
- Click "Upload New Document"
- Select PDF, DOCX, or image files
- Wait for AI processing to complete

5. **Analyze Documents**
- View simplified clauses with risk levels
- Check deadlines and obligations
- Use the Q&A feature to ask questions

6. **Dashboard**
- Monitor upcoming deadlines
- Track high-risk alerts
- View document statistics

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/check-auth` - Check authentication status

### Documents
- `POST /api/documents/upload` - Upload and process document
- `GET /api/documents/` - Get user's documents
- `GET /api/documents/<id>` - Get specific document with clauses
- `DELETE /api/documents/<id>` - Delete document
- `GET /api/documents/dashboard` - Get dashboard data

### AI Agents
- `POST /api/agents/process-document/<id>` - Process document through AI pipeline
- `POST /api/agents/ask-question` - Ask question about documents
- `GET /api/agents/suggested-questions` - Get suggested questions
- `POST /api/agents/analyze-risks/<id>` - Detailed risk analysis

## Features in Detail

### Document Processing Pipeline
1. **Upload**: File validation and storage
2. **Text Extraction**: OCR for images, direct extraction for PDFs/DOCX
3. **Preprocessing**: Clean and structure text into sections
4. **Classification**: AI categorizes each clause by type and risk
5. **Simplification**: Transform legal language to plain English
6. **Risk Analysis**: Identify risks, deadlines, and obligations
7. **Storage**: Save processed data for future reference

### Security Features
- Session-based authentication
- File type validation
- Size limits (16MB max)
- User data isolation
- Secure file storage

### Supported Document Types
- **Contracts**: Employment, rental, service agreements
- **Legal Documents**: Terms of service, privacy policies
- **Financial**: Loan agreements, insurance policies
- **File Formats**: PDF, DOCX, DOC, JPEG, PNG, BMP, TIFF

## Development

### Adding New Features
1. **New AI Agent**: Create in `backend/agents/`
2. **Database Model**: Add to `backend/models/`
3. **API Route**: Define in `backend/routes/`
4. **Frontend**: Update templates and JavaScript

### Testing
```bash
# Run the application in development mode
FLASK_ENV=development python backend/app.py
```

## Troubleshooting

### Common Issues

1. **MongoDB Atlas Connection Error**
   - Verify connection string in `.env` matches your Atlas cluster
   - Check database user credentials
   - Ensure IP address is whitelisted (or use 0.0.0.0/0 for development)
   - Verify network access settings in Atlas

2. **OCR Not Working**
   - Install Tesseract: `sudo apt-get install tesseract-ocr`
   - Verify installation: `tesseract --version`

3. **Google API Errors**
   - Verify API key in `.env`
   - Check API quotas and billing
   - Ensure Gemini API is enabled in Google Cloud Console

4. **File Upload Fails**
   - Check file size (max 16MB)
   - Verify upload directory permissions
   - Ensure supported file type

