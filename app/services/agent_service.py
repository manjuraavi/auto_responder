"""
Agent Service for managing and coordinating multiple AI agents.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import openai
from app.agents.base_agent import AgentState
from app.config.settings import settings
from app.services.vector_service import VectorService
from app.utils.exceptions import AIServiceException
from app.agents.response_generator import ResponseGeneratorAgent
from app.agents.context_retriever import ContextRetrieverAgent
from app.agents.intent_classifier import IntentClassifierAgent

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(
        self,
        current_user: Optional[Dict[str, Any]] = None,
        response_agent: Optional[ResponseGeneratorAgent] = None,
        context_agent: Optional[ContextRetrieverAgent] = None,
        intent_agent: Optional[IntentClassifierAgent] = None
    ):
        """
        Initialize agent service with user context and optional agent instances.
        
        Args:
            current_user: Current authenticated user information
            response_agent: Optional pre-initialized response generator agent
            context_agent: Optional pre-initialized context retriever agent
            intent_agent: Optional pre-initialized intent classifier agent
        """
        # Initialize user context if provided
        if current_user:
            self.user_email = current_user.get('email')
            self.user_id = current_user.get('sub')
            self.credentials = current_user.get('tokens', {})
            
            if not self.user_email or not self.user_id or not self.credentials:
                raise AIServiceException("Invalid user context for agent service")
        
        # Initialize OpenAI
        openai.api_key = settings.OPENAI_API_KEY
        
        # Initialize vector service
        self.vector_service = VectorService()
        self.vector_service.initialize()
        
        # Initialize agents - use provided instances or create new ones
        self.response_agent = response_agent or ResponseGeneratorAgent(vector_service=self.vector_service)
        self.context_agent = context_agent or ContextRetrieverAgent(vector_service=self.vector_service)
        self.intent_agent = intent_agent or IntentClassifierAgent(vector_service=self.vector_service)
        
        logger.info(f"Agent service initialized{f' for user: {self.user_email}' if current_user else ''}")
    
    async def verify_connection(self) -> bool:
        """Verify all agents are properly initialized"""
        try:
            # Verify each agent has required components
            if not self.response_agent or not self.context_agent or not self.intent_agent:
                return False
                
            # Additional verification could be added here
            return True
        except Exception as e:
            logger.error(f"Failed to verify agent connections: {str(e)}")
            return False

    async def process_email(self, email_content: str, email_subject: str = "") -> Dict[str, Any]:
        """Process an email through all agents"""
        try:
            # Step 1: Classify intent
            intent_result = await self.intent_agent.process(
                AgentState(
                    email_content=email_content,
                    subject=email_subject
                )
            )
            
            if not intent_result.success:
                raise AIServiceException(f"Intent classification failed: {intent_result.error}")
            
            # Step 2: Retrieve relevant context
            context_result = await self.context_agent.process(
                AgentState(
                    email_content=email_content,
                    subject=email_subject,
                    intent=intent_result.data.get("intent")
                )
            )
            
            if not context_result.success:
                raise AIServiceException(f"Context retrieval failed: {context_result.error}")
            
            # Step 3: Generate response
            response_result = await self.response_agent.process(
                AgentState(
                    email_content=email_content,
                    subject=email_subject,
                    intent=intent_result.data.get("intent"),
                    contexts=context_result.data.get("contexts", [])
                )
            )
            
            if not response_result.success:
                raise AIServiceException(f"Response generation failed: {response_result.error}")
            
            return {
                "response": response_result.data.get("response"),
                "intent": intent_result.data,
                "context": context_result.data,
                "metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "response_confidence": response_result.data.get("confidence", 0.0),
                    "intent_confidence": intent_result.data.get("confidence", 0.0)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to process email: {str(e)}")
            raise AIServiceException(f"Failed to process email: {str(e)}")

    async def generate_response(self, email_content: str, email_subject: str, context_length: int = 5) -> Dict[str, Any]:
        """Generate AI response for an email"""
        try:
            # Get relevant context from vector store
            context_docs = self.vector_service.query_similar(
                query=email_content,
                n_results=context_length,
                filter_dict={"user_id": self.user_id}
            )
            
            # Prepare prompt
            system_prompt = self._create_system_prompt(context_docs)
            user_prompt = self._create_user_prompt(email_subject, email_content)
            
            # Generate response using OpenAI
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            generated_text = response.choices[0].message.content
            
            return {
                "content": generated_text,
                "context_used": context_docs,
                "confidence_score": response.choices[0].finish_reason == "stop"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            raise AIServiceException(f"Failed to generate response: {str(e)}")

    async def classify_intent(self, email_subject: str, email_content: str) -> Dict[str, Any]:
        """Classify email intent"""
        try:
            # Prepare prompt for intent classification
            prompt = f"""Classify the intent of this email and extract key entities.
Email subject: {email_subject}
Email content: {email_content}

Provide the classification in JSON format with:
- Primary intent
- Confidence score (0-1)
- Key entities mentioned
"""
            client = openai.OpenAI(api_key=openai.api_key)

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an email intent classifier."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            # Parse the JSON response
            try:
                import json
                result = json.loads(response.choices[0].message.content)
                return result
            except:
                # Fallback if JSON parsing fails
                return {
                    "intent": "unknown",
                    "confidence": 0.0,
                    "entities": {}
                }
                
        except Exception as e:
            logger.error(f"Failed to classify intent: {str(e)}")
            raise AIServiceException(f"Failed to classify intent: {str(e)}")

    def _create_system_prompt(self, context_docs: List[Dict[str, Any]]) -> str:
        """Create system prompt with context"""
        context_text = "\n\n".join([
            f"Document: {doc['metadata']['filename']}\nContent: {doc['content'][:500]}..."
            for doc in context_docs
        ])
        
        return f"""You are an intelligent email response generator.
Your task is to generate appropriate, professional responses to emails.
Use the following context documents to inform your response:

{context_text}

Guidelines:
1. Be professional and courteous
2. Use relevant information from the context
3. Keep responses concise but complete
4. Maintain appropriate tone
5. Include specific details when available"""

    def _create_user_prompt(self, subject: str, content: str) -> str:
        """Create user prompt from email"""
        return f"""Please generate a response to this email:

Subject: {subject}
Content:
{content}

Generate a professional response that addresses the email's content and questions."""

    async def retrieve_context(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Retrieve relevant context for a query"""
        try:
            # Query vector store
            results = self.vector_service.query_similar(
                query=query,
                n_results=max_results,
                filter_dict={"user_id": self.user_id}
            )
            
            return {
                "relevant_documents": results,
                "similarity_scores": [doc.get('distance', 0) for doc in results]
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve context: {str(e)}")
            raise AIServiceException(f"Failed to retrieve context: {str(e)}")
