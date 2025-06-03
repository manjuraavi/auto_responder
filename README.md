# Gmail Auto-Responder SaaS

An AI-powered SaaS platform for automated, context-aware email responses and document management, leveraging semantic search, vector databases, and LLMs for intelligent email automation.

---

## 🌟 Features

### 🔐 Authentication & Security
- Google OAuth2 login (secure, no password storage)
- JWT-based session management with secure HTTP-only cookies
- Per-user rate limiting on sensitive endpoints (3 replies/minute)
- CORS and comprehensive security middleware
- No sensitive tokens exposed to frontend

### 📧 Advanced Email Management
- List, search, and filter emails (by unread, keyword)
- View email details and complete conversation threads
- Generate AI-powered suggested replies using OpenAI GPT-4
- Approve, edit, and send AI-generated replies
- Real-time email processing and monitoring
- Auto-mark emails as read after reply
- Context-aware response generation

### 📄 Smart Document Management
- Upload, list, and delete documents (PDF, DOCX, TXT)
- Download and organize document library
- Advanced semantic search using vector embeddings
- Document-based context for email responses
- Store document metadata and vector embeddings
- Configurable similarity thresholds

### 🤖 AI Agents & Intelligence
- **Context Retriever Agent**: Finds relevant document/email context
- **Intent Classifier Agent**: Understands email purpose and tone
- **Response Generator Agent**: Creates contextually appropriate replies
- Multi-modal AI processing for comprehensive understanding
- Semantic similarity matching for accurate responses

### 🔍 Advanced Search Capabilities
- **Vector-based semantic search** for emails and documents
- **Gmail API integration** for native email search
- Configurable similarity thresholds and ranking
- Cross-document context retrieval

### 📊 Health Monitoring & Analytics
- Comprehensive `/health` endpoint with system metrics
- Service connection monitoring (Gmail, vector DB, document service)
- System performance tracking (CPU, memory, disk, threads)
- Response time analytics for key endpoints
- Real-time status dashboard

### ⚡ Performance & Rate Management
- Intelligent per-user rate limiting (configurable limits)
- 429 error handling with user-friendly notifications
- Optimized vector database queries
- Async processing for better performance

### 🎨 Modern Frontend Experience
- **React-based** responsive web interface
- Secure login and logout flows with session management
- Intuitive dashboard with organized tabs (Emails, Documents, Settings, Help)
- Real-time toast notifications for all actions
- Document upload interface
- Rich email editor with AI response preview
- Mobile-responsive design
- Help documentation and onboarding guidance

---

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI with Pydantic validation
- **Server**: Uvicorn with async support
- **Authentication**: Google OAuth2 + JWT
- **Rate Limiting**: SlowAPI with Redis backend
- **Monitoring**: psutil for system metrics

### AI & Machine Learning
- **LLM**: OpenAI GPT-4 for response generation
- **Agent Orchestration**: LangChain & LangGraph for multi-agent workflows
- **Embeddings**: HuggingFace Transformers + Sentence Transformers
- **Vector Store**: ChromaDB with persistence
- **Search**: Hybrid semantic + keyword search

### Frontend
- **Framework**: React 18 with hooks
- **Routing**: React Router v6
- **Styling**: Tailwind CSS with custom components
- **Notifications**: React Toastify
- **State Management**: React Context + hooks

### Database & Storage
- **Vector DB**: ChromaDB for embeddings and semantic search
- **File Storage**: Local filesystem with configurable upload directory
- **Session Store**: JWT tokens

### External APIs
- **Gmail API**: Full read/write access with proper scoping
- **OpenAI API**: GPT-4 integration with usage monitoring
- **Google OAuth2**: Secure authentication flow

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Node.js 16+ (for React frontend)
- Google Cloud Project with Gmail API enabled
- OpenAI API key
- Chrome browser (recommended)

### 1. Clone and Install

```bash
git clone <https://github.com/manjuraavi/auto_responder.git>
cd saas_auto_responder

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable the Gmail API
4. Configure OAuth consent screen:
   - Add required scopes:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/gmail.modify`
     - `https://www.googleapis.com/auth/userinfo.email`
     - `https://www.googleapis.com/auth/userinfo.profile`
5. Create OAuth 2.0 Client ID:
   - Application type: Web application
   - Authorized redirect URIs:
     - `http://localhost:8000/api/auth/google/callback`
     - `http://localhost:3000/auth/callback`

### 3. Environment Configuration

```bash
# Copy template
cp .env.template .env

# Edit .env file with your credentials
```

Required environment variables:
```env
# Google OAuth2
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# Gmail API
GMAIL_SCOPES=["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.modify"]

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Security
SECRET_KEY=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Application
FRONTEND_URL=http://localhost:3000
UPLOAD_DIR=uploads
ENVIRONMENT=development
MAX_FILE_SIZE=10485760
ALLOWED_FILE_TYPES=pdf,docx,txt

# Rate Limiting
RATE_LIMIT_REPLIES_PER_MINUTE=3
RATE_LIMIT_QUERIES_PER_MINUTE=10
```

### 4. Run the Application

```bash
# Terminal 1: Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start React frontend
cd frontend
npm run dev
```

### 5. Access the Application

- **React App**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## 📖 API Documentation

### Authentication Endpoints
```
POST /api/auth/google           # Start Google OAuth2 flow
GET  /api/auth/google/callback  # OAuth2 callback handler
POST /api/auth/logout          # Logout and clear session
GET  /api/auth/me              # Get current user info
```

### Email Management
```
GET    /api/emails/                           # List emails with advanced filters
GET    /api/emails/{email_id}                 # Get detailed email info
GET    /api/emails/{email_id}/thread          # Get complete conversation thread
POST   /api/emails/{email_id}/reply           # Generate and send AI reply (rate limited)
POST   /api/emails/{email_id}/generate-response # Generate suggested reply (rate limited)
PATCH  /api/emails/{email_id}/mark-read       # Mark email as read
GET    /api/emails/search                     # Advanced email search
```

### Document Management
```
GET    /api/documents/                    # List all documents with metadata
POST   /api/documents/upload             # Upload new document
POST   /api/documents/query              # Semantic/hybrid/keyword search
DELETE /api/documents/{doc_id}           # Delete document
GET    /api/documents/{doc_id}/download  # Download document file
GET    /api/documents/{doc_id}/info      # Get document metadata
```

### AI Agent Endpoints
```
POST /api/agents/context-retrieval     # Get relevant context for email
POST /api/agents/intent-classification # Classify email intent and tone
POST /api/agents/response-generation   # Generate contextual response
```

### System & Monitoring
```
GET /health        # Comprehensive health check and metrics
GET /              # System information and status
GET /api/metrics   # Detailed performance metrics
```

---

## 💡 Usage Examples

### 1. Basic Email Auto-Response Flow
1. **Login**: Click "Login with Gmail" → Authenticate
2. **Upload Context**: Add company docs, FAQs, policies
3. **View Emails**: Browse inbox with smart filtering
4. **Generate Response**: Click "Generate Reply" on any email
5. **Review & Send**: Edit AI response and send with one click

### 2. Document-Based Context Setup
1. Upload relevant documents (policies, FAQs, templates)
2. System automatically creates vector embeddings
3. AI uses semantic search to find relevant context
4. Responses are generated with appropriate context

---

## 🔒 Security Features

- **OAuth2 Integration**: Secure Google authentication
- **JWT Sessions**: Encrypted session management
- **Rate Limiting**: Prevent API abuse
- **Input Validation**: Comprehensive request validation
- **CORS Protection**: Configurable cross-origin policies
- **File Upload Security**: Type validation and size limits
- **Error Handling**: Secure error responses without data leaks

---

## 📊 Monitoring & Health Checks

The `/health` endpoint provides comprehensive system monitoring:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "gmail_api": "connected",
    "vector_db": "healthy",
    "document_service": "operational",
    "openai_api": "connected"
  },
  "system_metrics": {
    "cpu_usage": 15.2,
    "memory_usage": 45.8,
    "disk_usage": 67.3,
    "active_threads": 12
  },
  "performance": {
    "avg_response_time": 145,
    "total_requests": 1250,
    "error_rate": 0.8
  }
}
```

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [OpenAI](https://openai.com/) - GPT-4 AI models
- [Google Gmail API](https://developers.google.com/gmail/api) - Email integration
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Sentence Transformers](https://www.sbert.net/) - Semantic embeddings
- [React](https://reactjs.org/) - Frontend framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS

---

**Built with ❤️ for intelligent email automation**