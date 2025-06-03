# Gmail Auto-Responder

An AI-powered email auto-response system using Gmail API, FastAPI, and Streamlit.

## Features

- Gmail OAuth2 integration
- AI-powered response generation using GPT-4
- Document-based context for responses
- Streamlit web interface
- Real-time email processing

## Prerequisites

1. Python 3.8 or higher
2. A Google Cloud Project with Gmail API enabled
3. OpenAI API key
4. Chrome browser (recommended)

## Setup Instructions

1. **Clone the repository**
```bash
git clone <repository-url>
cd saas_auto_responder
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run setup script**
```bash
python setup.py
```

4. **Configure Google OAuth2**

a. Go to [Google Cloud Console](https://console.cloud.google.com)
b. Create a new project or select existing one
c. Enable Gmail API
d. Configure OAuth consent screen:
   - Add scopes:
     - https://www.googleapis.com/auth/gmail.readonly
     - https://www.googleapis.com/auth/gmail.compose
     - https://www.googleapis.com/auth/gmail.modify
     - https://www.googleapis.com/auth/userinfo.email
     - https://www.googleapis.com/auth/userinfo.profile
e. Create OAuth 2.0 Client ID:
   - Application type: Web application
   - Add authorized redirect URIs:
     - http://localhost:3000/
     - http://localhost:8000/api/auth/callback

5. **Configure environment**
```bash
cp .env.template .env
```
Edit `.env` file and add:
- Your OpenAI API key
- Google OAuth credentials
- Generate a random secret key

## Running the Application

1. **Start the backend server**
```bash
uvicorn app.main:app --reload
```

2. **Start the Streamlit frontend**
```bash
streamlit run streamlit_app.py
```

3. **Access the application**
- Open browser to http://localhost:8501
- Click "Login with Gmail"
- Accept the permissions
- Start using the auto-responder!

## Usage

1. **Login**: Use the "Login with Gmail" button
2. **Upload Context**: Add documents that contain response context
3. **View Emails**: See your recent emails
4. **Generate Responses**: Click "Auto-Respond" on any email
5. **Send**: Review and send the generated responses

## Troubleshooting

1. **Authentication Issues**
- Verify Google OAuth credentials
- Check redirect URIs
- Clear browser cookies

2. **Email Access Issues**
- Verify Gmail API is enabled
- Check required scopes are approved
- Ensure account has emails

3. **Response Generation Issues**
- Verify OpenAI API key
- Check context documents are uploaded
- Verify internet connection

## Support

For issues and questions, please create an issue in the repository.

## License

MIT License - See LICENSE file for details 