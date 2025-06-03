"""
Response Generation Agent for creating contextual email replies.
Generates appropriate responses based on intent classification and retrieved context.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from langchain.tools import BaseTool, tool
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
import re
from datetime import datetime

from .base_agent import BaseAgent, AgentState, AgentResult

logger = logging.getLogger(__name__)


class ResponseGenerationResult(BaseModel):
    """Structured result for response generation"""
    response: str = Field(description="Generated email response")
    tone: str = Field(description="Tone of the response (professional, friendly, apologetic, etc.)")
    urgency: str = Field(description="Response urgency level")
    confidence: float = Field(description="Confidence in response quality (0-1)")
    key_points: List[str] = Field(default_factory=list, description="Key points addressed")
    followup_needed: bool = Field(description="Whether follow-up is needed")
    attachments_suggested: List[str] = Field(default_factory=list, description="Suggested attachments")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional response metadata")


class ToneAnalysisTool(BaseTool):
    """Tool for analyzing appropriate response tone based on intent and content"""
    
    name = "tone_analyzer"
    description = "Analyze email to determine appropriate response tone"
    
    TONE_MAPPING = {
        "question": ["helpful", "informative", "professional"],
        "complaint": ["apologetic", "understanding", "solution-focused"],
        "escalation": ["urgent", "professional", "reassuring"],
        "request": ["accommodating", "professional", "helpful"]
    }
    
    NEGATIVE_INDICATORS = [
        "frustrated", "disappointed", "angry", "upset", "terrible",
        "awful", "horrible", "unacceptable", "disgusted", "furious"
    ]
    
    POSITIVE_INDICATORS = [
        "thank", "appreciate", "great", "excellent", "wonderful",
        "pleased", "satisfied", "happy", "love", "impressed"
    ]
    
    def _run(self, email_content: str, intent: str, sender_history: Optional[Dict] = None) -> Dict:
        """Analyze email to determine appropriate response tone"""
        content_lower = email_content.lower()
        
        # Check for emotional indicators
        negative_count = sum(1 for word in self.NEGATIVE_INDICATORS if word in content_lower)
        positive_count = sum(1 for word in self.POSITIVE_INDICATORS if word in content_lower)
        
        # Determine base tone from intent
        base_tones = self.TONE_MAPPING.get(intent, ["professional"])
        
        # Adjust tone based on sentiment
        if negative_count > positive_count and negative_count > 0:
            if "apologetic" not in base_tones:
                base_tones.insert(0, "apologetic")
            if "understanding" not in base_tones:
                base_tones.append("understanding")
        elif positive_count > negative_count and positive_count > 0:
            if "friendly" not in base_tones:
                base_tones.append("friendly")
        
        # Check for urgency indicators
        urgency_indicators = ["urgent", "asap", "immediately", "emergency", "critical"]
        is_urgent = any(indicator in content_lower for indicator in urgency_indicators)
        
        # Determine primary tone
        primary_tone = base_tones[0]
        
        # Check for VIP customer (if history provided)
        is_vip = False
        if sender_history:
            is_vip = sender_history.get("vip_status", False)
        
        return {
            "primary_tone": primary_tone,
            "secondary_tones": base_tones[1:],
            "emotional_sentiment": "negative" if negative_count > positive_count else "positive" if positive_count > 0 else "neutral",
            "urgency_detected": is_urgent,
            "vip_customer": is_vip,
            "tone_confidence": min(1.0, (len(base_tones) + negative_count + positive_count) * 0.2)
        }


class ResponseTemplateTool(BaseTool):
    """Tool for selecting and customizing response templates"""
    
    name = "template_selector"
    description = "Select and customize response templates based on intent and context"
    
    TEMPLATES = {
        "question_general": """
Thank you for your inquiry regarding {topic}.

{context_information}

{specific_answer}

If you have any additional questions, please don't hesitate to reach out.

Best regards,
{signature}
""",
        
        "question_technical": """
Thank you for contacting us about {topic}.

I understand you're experiencing {issue_description}. Here's what I can help you with:

{solution_steps}

{context_information}

If these steps don't resolve the issue, please let me know and I'll be happy to provide further assistance.

Best regards,
{signature}
""",
        
        "complaint_acknowledgment": """
Thank you for bringing this matter to our attention, and I sincerely apologize for {issue_description}.

I understand your frustration, and I want to make this right. Here's what I'm going to do:

{action_items}

{context_information}

{timeline_information}

I'll personally ensure this is resolved promptly. Please don't hesitate to contact me directly if you have any concerns.

Sincerely,
{signature}
""",
        
        "escalation_urgent": """
Thank you for your message. I understand the urgency of your situation regarding {topic}.

I am immediately escalating this matter to ensure you receive prompt resolution:

{escalation_actions}

{immediate_steps}

You can expect to hear from {contact_person} within {timeframe}.

{context_information}

Thank you for your patience as we work to resolve this matter quickly.

Best regards,
{signature}
""",
        
        "request_fulfillment": """
Thank you for your request regarding {topic}.

I'm pleased to help you with {request_description}. Here's what I can provide:

{fulfillment_details}

{context_information}

{next_steps}

Please let me know if you need anything else.

Best regards,
{signature}
""",
        
        "request_cannot_fulfill": """
Thank you for your request regarding {topic}.

I understand you're looking for {request_description}. While I'm not able to fulfill this exact request due to {limitation_reason}, I can offer the following alternatives:

{alternative_options}

{context_information}

I hope one of these alternatives will work for your needs. Please let me know how I can best assist you.

Best regards,
{signature}
"""
    }
    
    def _run(self, intent: str, email_content: str, context: str, tone: str) -> Dict:
        """Select appropriate template and prepare customization variables"""
        
        # Determine template type
        template_key = self._select_template_key(intent, email_content, tone)
        template = self.TEMPLATES.get(template_key, self.TEMPLATES["question_general"])
        
        # Extract customization variables
        variables = self._extract_variables(email_content, context, intent)
        
        return {
            "template": template,
            "template_key": template_key,
            "variables": variables,
            "customization_needed": self._identify_customization_needs(template, variables)
        }
    
    def _select_template_key(self, intent: str, email_content: str, tone: str) -> str:
        """Select the most appropriate template"""
        content_lower = email_content.lower()
        
        if intent == "question":
            if any(tech_word in content_lower for tech_word in ["error", "bug", "not working", "technical", "setup"]):
                return "question_technical"
            return "question_general"
        
        elif intent == "complaint":
            return "complaint_acknowledgment"
        
        elif intent == "escalation":
            return "escalation_urgent"
        
        elif intent == "request":
            # Determine if request can likely be fulfilled
            negative_indicators = ["cannot", "unable", "not possible", "restricted", "policy"]
            if any(indicator in content_lower for indicator in negative_indicators):
                return "request_cannot_fulfill"
            return "request_fulfillment"
        
        return "question_general"
    
    def _extract_variables(self, email_content: str, context: str, intent: str) -> Dict:
        """Extract variables for template customization"""
        variables = {
            "topic": "your inquiry",
            "signature": "Customer Service Team",
            "context_information": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        # Extract topic from email content (simple approach)
        sentences = email_content.split('.')
        if sentences:
            first_sentence = sentences[0].strip()
            first_sentence = sentences[0].strip()
            # Try to extract a topic from the first sentence using a simple heuristic
            topic_match = re.search(r"(about|regarding|concerning|on)\s+([A-Za-z0-9\s\-_,]+)", first_sentence, re.IGNORECASE)
            if topic_match:
                variables["topic"] = topic_match.group(2).strip().capitalize()
            else:
                # Fallback: use first few words as topic
                variables["topic"] = " ".join(first_sentence.split()[:6]).capitalize() or "your inquiry"

        # Add context information if available
        if context:
            variables["context_information"] = context

        # Add more variables based on intent if needed
        if intent == "complaint":
            # Try to extract issue description
            issue_match = re.search(r"(problem|issue|error|trouble|difficulty)\s*(with|in|regarding)?\s*([A-Za-z0-9\s\-_,]+)?", email_content, re.IGNORECASE)
            if issue_match and issue_match.group(3):
                variables["issue_description"] = issue_match.group(3).strip().capitalize()
            else:
                variables["issue_description"] = "the issue you described"
        elif intent == "request":
            # Try to extract request description
            request_match = re.search(r"(request|would like|please)\s*(for|to)?\s*([A-Za-z0-9\s\-_,]+)?", email_content, re.IGNORECASE)
            if request_match and request_match.group(3):
                variables["request_description"] = request_match.group(3).strip().capitalize()
            else:
                variables["request_description"] = "your request"
        elif intent == "escalation":
            variables["escalation_actions"] = "Escalating to the appropriate team"
            variables["immediate_steps"] = "We are prioritizing your case"
            variables["contact_person"] = "our escalation manager"
            variables["timeframe"] = "24 hours"
        # Add placeholders for other template variables as needed
        # (e.g., solution_steps, action_items, timeline_information, fulfillment_details, next_steps, alternative_options, limitation_reason)
        # These can be filled in by downstream LLM or business logic

        return variables


class ResponseGeneratorAgent(BaseAgent):
    """
    Agent specialized in generating contextual email responses.
    Uses tone analysis and template selection for appropriate responses.
    """
    
    def __init__(self, vector_service, **kwargs):
        # Initialize tools
        tools = [
            ToneAnalysisTool(),
            ResponseTemplateTool()
        ]
        
        super().__init__(
            name="response_generator",
            tools=tools,
            vector_service=vector_service,
            **kwargs
        )
        
        # Store vector service
        self.vector_service = vector_service
        
        # Response generation prompt template
        self.generation_prompt = PromptTemplate(
            input_variables=["email_content", "intent", "context", "tone_analysis", "template_data"],
            template="""
You are an expert email response generator. Generate a contextually appropriate response using the provided information.

Original Email:
{email_content}

Analysis:
- Intent: {intent}
- Context: {context}
- Tone Analysis: {tone_analysis}

Template Data:
{template_data}

Generate a response that:
1. Addresses the main points/concerns
2. Maintains appropriate tone
3. Includes relevant context
4. Is professional and helpful
5. Follows the selected template structure

Your response should be natural and not sound templated, while maintaining professionalism.
"""
        )
    
    async def process(self, state: AgentState) -> AgentResult:
        """Process the email and generate an appropriate response"""
        try:
            if not await self.validate_input(state):
                return AgentResult(
                    success=False,
                    error="Invalid input state"
                )
            
            # Analyze tone
            tone_result = await self.execute_with_tools(
                input_text=state.email_content or "",
                context={
                    "intent": state.intent,
                    "sender": state.sender
                }
            )
            
            if not tone_result.success:
                return AgentResult(
                    success=False,
                    error=f"Tone analysis failed: {tone_result.error}"
                )
            
            # Select and customize template
            template_result = await self.execute_with_tools(
                input_text=state.email_content or "",
                context={
                    "intent": state.intent,
                    "context": state.context,
                    "tone": tone_result.data.get("output", {}).get("primary_tone", "professional")
                }
            )
            
            if not template_result.success:
                return AgentResult(
                    success=False,
                    error=f"Template selection failed: {template_result.error}"
                )
            
            # Generate final response using LLM
            response = await self._generate_response(
                email_content=state.email_content or "",
                intent=state.intent or "general",
                context=state.context or "",
                tone_analysis=tone_result.data.get("output", {}),
                template_data=template_result.data.get("output", {})
            )
            
            if not response:
                return AgentResult(
                    success=False,
                    error="Failed to generate response"
                )
            
            return AgentResult(
                success=True,
                data={
                    "response": response,
                    "tone_analysis": tone_result.data.get("output", {}),
                    "template_data": template_result.data.get("output", {})
                },
                metadata={
                    "response_length": len(response),
                    "generation_timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            error_msg = f"Response generation failed: {str(e)}"
            logger.error(error_msg)
            return AgentResult(
                success=False,
                error=error_msg
            )
    
    async def validate_input(self, state: AgentState) -> bool:
        """Validate required input state"""
        return bool(
            state and
            state.email_content and
            state.intent
        )
    
    async def _generate_response(
        self,
        email_content: str,
        intent: str,
        context: str,
        tone_analysis: Dict,
        template_data: Dict
    ) -> Optional[str]:
        """Generate the final response using LLM"""
        try:
            # Prepare prompt
            prompt = self.generation_prompt.format(
                email_content=email_content[:2000],  # Limit content length
                intent=intent,
                context=context[:1000],  # Limit context length
                tone_analysis=str(tone_analysis),
                template_data=str(template_data)
            )
            
            # Get LLM response
            response = await self.llm.ainvoke(prompt)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return None