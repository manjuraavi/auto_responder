"""
Intent Classification Agent for email analysis.
Classifies incoming emails into categories: Question, Complaint, Escalation, Request.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any, Type
from langchain.tools import BaseTool, tool
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field, validator

from .base_agent import BaseAgent, AgentState, AgentResult

logger = logging.getLogger(__name__)


class IntentClassificationResult(BaseModel):
    """Result of intent classification"""
    intent: str = Field(description="Classified intent of the email")
    confidence: float = Field(description="Confidence score of the classification", ge=0.0, le=1.0)
    sub_intents: List[str] = Field(default_factory=list, description="List of secondary intents")
    explanation: str = Field(description="Explanation of the classification")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError('Confidence must be between 0 and 1')
        return v

    @validator('intent')
    def validate_intent(cls, v):
        """Ensure intent is not empty"""
        if not v.strip():
            raise ValueError('Intent cannot be empty')
        return v.strip().lower()

    class Config:
        """Pydantic config"""
        validate_assignment = True
        extra = "allow"


class KeywordAnalysisTool(BaseTool):
    """Tool for analyzing keywords in email content"""
    
    name = "keyword_analyzer"
    description = "Analyze email content for intent-related keywords and patterns"
    
    # Predefined keyword mappings for different intents
    INTENT_KEYWORDS = {
        "question": [
            "how", "what", "when", "where", "why", "which", "who",
            "can you", "could you", "would you", "do you know",
            "help me understand", "clarify", "explain", "?",
            "wondering", "curious", "confused", "unclear"
        ],
        "complaint": [
            "disappointed", "frustrated", "angry", "upset", "dissatisfied",
            "problem", "issue", "bug", "error", "broken", "not working",
            "terrible", "awful", "horrible", "worst", "bad experience",
            "complain", "complaint", "unacceptable", "poor service"
        ],
        "escalation": [
            "urgent", "emergency", "asap", "immediately", "critical",
            "manager", "supervisor", "escalate", "higher up",
            "legal action", "lawsuit", "attorney", "lawyer",
            "unresolved", "no response", "ignored", "deadline"
        ],
        "request": [
            "please", "can you", "could you", "would you", "need",
            "want", "require", "request", "asking for", "looking for",
            "help with", "assistance", "support", "provide", "send"
        ]
    }
    
    URGENCY_KEYWORDS = {
        "high": [
            "urgent", "emergency", "asap", "immediately", "critical",
            "deadline", "time-sensitive", "rush", "priority"
        ],
        "medium": [
            "soon", "quickly", "prompt", "timely", "important",
            "needs attention", "follow up"
        ],
        "low": [
            "when convenient", "no rush", "whenever", "at your convenience",
            "low priority", "informational"
        ]
    }
    
    def _run(self, email_content: str) -> Dict:
        """Analyze email content for keywords and patterns"""
        content_lower = email_content.lower()
        
        # Count keyword matches for each intent
        intent_scores = {}
        found_keywords = {}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            matches = []
            score = 0
            
            for keyword in keywords:
                if keyword in content_lower:
                    matches.append(keyword)
                    # Weight certain keywords more heavily
                    if keyword in ["urgent", "emergency", "asap", "complaint"]:
                        score += 2
                    else:
                        score += 1
            
            intent_scores[intent] = score
            found_keywords[intent] = matches
        
        # Determine urgency
        urgency = "low"
        for level, keywords in self.URGENCY_KEYWORDS.items():
            if any(keyword in content_lower for keyword in keywords):
                urgency = level
                if level == "high":  # High urgency takes precedence
                    break
        
        # Additional pattern analysis
        patterns = {
            "has_question_mark": "?" in email_content,
            "has_exclamation": "!" in email_content,
            "has_caps": any(word.isupper() and len(word) > 2 for word in email_content.split()),
            "word_count": len(email_content.split()),
            "sentence_count": len(re.split(r'[.!?]+', email_content))
        }
        
        return {
            "intent_scores": intent_scores,
            "found_keywords": found_keywords,
            "urgency": urgency,
            "patterns": patterns
        }


class SentimentAnalysisTool(BaseTool):
    """Tool for analyzing sentiment and emotional tone"""
    
    name = "sentiment_analyzer"
    description = "Analyze email sentiment and emotional tone"
    
    POSITIVE_WORDS = [
        "good", "great", "excellent", "wonderful", "amazing", "fantastic",
        "happy", "pleased", "satisfied", "thank", "appreciate", "love"
    ]
    
    NEGATIVE_WORDS = [
        "bad", "terrible", "awful", "horrible", "disappointed", "frustrated",
        "angry", "upset", "hate", "annoyed", "irritated", "dissatisfied"
    ]
    
    def _run(self, email_content: str) -> Dict:
        """Analyze sentiment of email content"""
        content_lower = email_content.lower()
        
        positive_count = sum(1 for word in self.POSITIVE_WORDS if word in content_lower)
        negative_count = sum(1 for word in self.NEGATIVE_WORDS if word in content_lower)
        
        # Calculate sentiment score
        total_words = len(content_lower.split())
        if total_words == 0:
            sentiment_score = 0
        else:
            sentiment_score = (positive_count - negative_count) / total_words
        
        # Determine sentiment category
        if sentiment_score > 0.02:
            sentiment = "positive"
        elif sentiment_score < -0.02:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "positive_words": positive_count,
            "negative_words": negative_count,
            "emotional_intensity": abs(sentiment_score)
        }


class IntentClassifierTool(BaseTool):
    """Tool for classifying email intent"""
    
    name = "intent_classifier"
    description = "Classify the intent of an email message"
    llm: Any = Field(description="Language model for intent classification")
    output_parser: JsonOutputParser = Field(default_factory=lambda: JsonOutputParser(pydantic_object=IntentClassificationResult))
    classification_prompt: PromptTemplate = Field(default_factory=lambda: PromptTemplate(
        input_variables=["email_content", "subject", "available_intents"],
        template="""
Analyze the following email and classify its primary intent.

Email Subject: {subject}
Email Content: {email_content}

Available Intents:
{available_intents}

Classify the email's intent and provide your analysis in the following JSON format:
{
    "intent": "primary_intent",
    "confidence": 0.0 to 1.0,
    "sub_intents": ["secondary_intent1", "secondary_intent2"],
    "explanation": "Brief explanation of classification",
    "metadata": {
        "key_phrases": ["relevant", "key", "phrases"],
        "sentiment": "positive/negative/neutral"
    }
}

Ensure the intent matches one of the available intents exactly.
"""
    ), description="Prompt template for intent classification")

    def __init__(self, llm: Any, **kwargs):
        """Initialize the tool with a language model"""
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, email_content: str, subject: str = "", available_intents: List[str] = None) -> Dict:
        """Classify email intent"""
        try:
            if available_intents is None:
                available_intents = [
                    "question",
                    "request",
                    "complaint",
                    "feedback",
                    "inquiry",
                    "other"
                ]
            
            prompt = self.classification_prompt.format(
                email_content=email_content[:1000],  # Limit length
                subject=subject or "No subject",
                available_intents="\n".join(f"- {intent}" for intent in available_intents)
            )
            
            response = self.llm.invoke(prompt)
            result = self.output_parser.parse(response.content)
            
            return result.dict()
            
        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}")
            return {
                "intent": "other",
                "confidence": 0.5,
                "sub_intents": [],
                "explanation": f"Classification failed: {str(e)}",
                "metadata": {"error": str(e)}
            }


class IntentClassifierAgent(BaseAgent):
    """
    Agent specialized in classifying email intents.
    Uses LLM-based classification with confidence scoring.
    """
    
    def __init__(self, vector_service, **kwargs):
        """
        Initialize the intent classifier agent.
        
        Args:
            vector_service: VectorService instance
            **kwargs: Additional arguments for base agent
        """
        # Initialize tools
        tools = [
            IntentClassifierTool(llm=kwargs.get('llm'))
        ]
        
        super().__init__(
            name="intent_classifier",
            tools=tools,
            vector_service=vector_service,
            **kwargs
        )
        
        # Store vector service reference
        self.vector_service = vector_service
        
        # Available intents
        self.available_intents = [
            "question",
            "request",
            "complaint",
            "feedback",
            "inquiry",
            "other"
        ]
    
    async def process(self, state: AgentState) -> AgentResult:
        """
        Classify the intent of an email.
        
        Args:
            state: Current agent state
            
        Returns:
            AgentResult with intent classification
        """
        try:
            if not state.email_content:
                return AgentResult(
                    success=False,
                    error="No email content provided for intent classification"
                )
            
            # Use intent classifier tool
            classifier_tool = self.get_tool("intent_classifier")
            if not classifier_tool:
                raise ValueError("Intent classifier tool not found")
            
            result = classifier_tool._run(
                email_content=state.email_content,
                subject=state.subject,
                available_intents=self.available_intents
            )
            
            return AgentResult(
                success=True,
                data=result,
                metadata={
                    "agent": self.name,
                    "classification_method": "llm_based"
                }
            )
            
        except Exception as e:
            error_msg = f"Intent classification failed: {str(e)}"
            logger.error(error_msg)
            return AgentResult(
                success=False,
                error=error_msg,
                metadata={"agent": self.name}
            )
    
    async def validate_input(self, state: AgentState) -> bool:
        """Validate input state for intent classification"""
        if not state.email_content:
            logger.error("No email content provided for intent classification")
            return False
        return True
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported intent categories"""
        return ["question", "complaint", "escalation", "request"]
    
    def analyze_intent_distribution(self, email_batch: List[str]) -> Dict:
        """
        Analyze intent distribution across a batch of emails.
        Useful for understanding email patterns and volumes.
        """
        results = {"question": 0, "complaint": 0, "escalation": 0, "request": 0}
        
        for email in email_batch:
            keyword_tool = KeywordAnalysisTool()
            analysis = keyword_tool._run(email)
            intent_scores = analysis.get("intent_scores", {})
            
            if intent_scores:
                primary_intent = max(intent_scores, key=intent_scores.get)
                results[primary_intent] += 1
        
        return results


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_intent_classifier():
        # Test email samples
        test_emails = [
            {
                "content": "I'm having trouble with my account login. Can you help me understand what's wrong?",
                "sender": "user@example.com",
                "subject": "Login Issues"
            },
            {
                "content": "This is absolutely terrible service! I've been waiting for hours and no one has responded. I want to speak to a manager immediately!",
                "sender": "angry@example.com",
                "subject": "URGENT: Terrible Service"
            },
            {
                "content": "Could you please send me the latest product catalog? I'm interested in making a purchase.",
                "sender": "customer@example.com",
                "subject": "Product Catalog Request"
            }
        ]
        
        classifier = IntentClassifierAgent()
        
        for email in test_emails:
            state = AgentState(
                email_content=email["content"],
                sender=email["sender"],
                subject=email["subject"]
            )
            
            result = await classifier.process(state)
            print(f"\nEmail: {email['subject']}")
            print(f"Classification: {result.data}")
    
    # Run test
    # asyncio.run(test_intent_classifier())