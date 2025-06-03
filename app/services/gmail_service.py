from typing import List, Dict, Optional, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
import base64
import json
import logging
from datetime import datetime

from app.services.document_service import DocumentService
from app.utils.exceptions import EmailServiceException
from app.config.settings import settings

logger = logging.getLogger(__name__)

class GmailService:
    def __init__(self, credentials_dict: Dict[str, Any], user_email: str):
        """Initialize Gmail service with credentials"""
        try:
            credentials = Credentials(
                token=credentials_dict.get('token'),
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=settings.GMAIL_SCOPES
            )
            
            self.service = build('gmail', 'v1', credentials=credentials)
            self.user_email = user_email
            logger.info(f"Gmail service initialized for user: {user_email}")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {str(e)}")
            raise EmailServiceException(f"Failed to initialize Gmail service: {str(e)}")

    @classmethod
    async def verify_connection(cls) -> bool:
        """Verify Gmail API connection is working"""
        try:
            # Since this is a class method and we don't have credentials,
            # we can only verify that the required settings are available
            required_settings = [
                settings.GOOGLE_CLIENT_ID,
                settings.GOOGLE_CLIENT_SECRET,
                settings.GMAIL_SCOPES
            ]
            
            if not all(required_settings):
                logger.error("Missing required Gmail API settings")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Failed to verify Gmail connection: {str(e)}")
            return False

    def list_messages(self, max_results: int = 50, query: str = "") -> List[Dict[str, Any]]:
        """List messages from Gmail inbox"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            detailed_messages = []
            
            for message in messages:
                msg_detail = self.get_message(message['id'])
                if msg_detail:
                    # Add unread status
                    msg_detail['is_unread'] = 'UNREAD' in msg_detail['labels']
                    detailed_messages.append(msg_detail)
            
            return detailed_messages
        except HttpError as error:
            logger.error(f"Failed to list messages: {str(error)}")
            raise EmailServiceException(f"Failed to list messages: {str(error)}")

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed message information"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            to_email = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
            
            # Get message body
            body = self._get_message_body(message['payload'])
            
            return {
                'id': message['id'],
                'thread_id': message['threadId'],
                'subject': subject,
                'from': from_email,
                'to': to_email,
                'body': body,
                'labels': message['labelIds'],
                'date': message['internalDate'],
                'is_unread': 'UNREAD' in message['labelIds']
            }
        except HttpError as error:
            logger.error(f"Failed to get message {message_id}: {str(error)}")
            return None

    def _get_message_body(self, payload: Dict[str, Any]) -> str:
        """Extract message body from payload"""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        
        return ""

    def send_message(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Send an email message"""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            send_kwargs = {
                'userId': 'me',
                'body': {'raw': raw_message}
            }
            
            if thread_id:
                send_kwargs['body']['threadId'] = thread_id
            
            sent_message = self.service.users().messages().send(**send_kwargs).execute()
            
            logger.info(f"Message sent successfully. Message ID: {sent_message['id']}")
            return sent_message
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            raise EmailServiceException(f"Failed to send message: {str(e)}")

    def modify_message(self, message_id: str, add_labels: List[str] = None, remove_labels: List[str] = None) -> Dict[str, Any]:
        """Modify message labels"""
        try:
            body = {
                'addLabelIds': add_labels or [],
                'removeLabelIds': remove_labels or []
            }
            
            result = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body=body
            ).execute()
            
            logger.info(f"Modified labels for message {message_id}")
            return result
        except HttpError as error:
            logger.error(f"Failed to modify message {message_id}: {str(error)}")
            raise EmailServiceException(f"Failed to modify message: {str(error)}")

    def get_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a thread"""
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            
            messages = []
            for message in thread['messages']:
                msg_detail = self._parse_message(message)
                if msg_detail:
                    messages.append(msg_detail)
            
            return messages
        except HttpError as error:
            logger.error(f"Failed to get thread {thread_id}: {str(error)}")
            raise EmailServiceException(f"Failed to get thread: {str(error)}")

    def _parse_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse message details from raw message"""
        try:
            headers = message['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            to_email = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            
            body = self._get_message_body(message['payload'])
            
            return {
                'id': message['id'],
                'subject': subject,
                'from': from_email,
                'to': to_email,
                'body': body,
                'date': date,
                'labels': message['labelIds']
            }
        except Exception as e:
            logger.error(f"Failed to parse message: {str(e)}")
            return None

    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        try:
            self.modify_message(
                message_id=message_id,
                remove_labels=['UNREAD']
            )
            return True
        except Exception as e:
            logger.error(f"Failed to mark message {message_id} as read: {str(e)}")
            return False

    def mark_as_unread(self, message_id: str) -> bool:
        """Mark a message as unread"""
        try:
            self.modify_message(
                message_id=message_id,
                add_labels=['UNREAD']
            )
            return True
        except Exception as e:
            logger.error(f"Failed to mark message {message_id} as unread: {str(e)}")
            return False

    def get_labels(self) -> List[Dict[str, Any]]:
        """Get Gmail labels/folders"""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Format labels
            formatted_labels = []
            for label in labels:
                formatted_labels.append({
                    "id": label['id'],
                    "name": label['name'],
                    "type": label['type'],  # 'system' or 'user'
                    "messageListVisibility": label.get('messageListVisibility', 'show'),
                    "labelListVisibility": label.get('labelListVisibility', 'labelShow')
                })
            
            return formatted_labels
        except Exception as e:
            logger.error(f"Failed to get labels: {str(e)}")
            raise EmailServiceException(f"Failed to get labels: {str(e)}")

    def load_all_to_vectordb(self):
        """
        Fetch all emails for the user and ingest them into the vector DB.
        """
        try:
            document_service = DocumentService(self.user_email)
            next_page_token = None
            total = 0
            while True:
                response = self.service.users().messages().list(
                    userId='me',
                    maxResults=100,
                    pageToken=next_page_token
                ).execute()
                messages = response.get('messages', [])
                for msg in messages:
                    msg_detail = self.get_message(msg['id'])
                    if msg_detail and msg_detail['body']:
                        document_service.process_email_content(
                            msg_detail['body'],
                            {
                                "subject": msg_detail['subject'],
                                "from": msg_detail['from'],
                                "to": msg_detail['to'],
                                "date": msg_detail['date'],
                                "gmail_id": msg_detail['id'],
                                "type": "email"  # Add this field to distinguish emails
                            }
                        )
                        total += 1
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            logger.info(f"Ingested {total} emails into vector DB for {self.user_email}")
        except Exception as e:
            logger.error(f"Failed to ingest all emails: {str(e)}")
            raise