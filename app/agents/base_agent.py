"""
Base agent class for the AI email assistant multi-agent system.
Uses LangGraph for workflow orchestration and state management.
"""

import logging
from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Annotated, Callable
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain.chat_models import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.agents import AgentAction, AgentFinish
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from typing import Union
import json
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Type definitions
AgentStateType = TypeVar("AgentStateType", bound=BaseModel)

class AgentState(BaseModel):
    """State model for agent interactions"""
    # Input state
    email_content: Optional[str] = None
    sender: Optional[str] = None
    subject: Optional[str] = None
    intent: Optional[str] = None
    context: Optional[str] = None
    
    # Execution state
    messages: List[BaseMessage] = Field(default_factory=list)
    actions: List[AgentAction] = Field(default_factory=list)
    action_results: List[str] = Field(default_factory=list)
    current_action: Optional[AgentAction] = None
    final_answer: Optional[str] = None
    
    # Output state
    response: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

class AgentResult(BaseModel):
    """Result model for agent operations"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the email assistant system.
    Implements LangGraph-based workflow orchestration.
    """
    
    def __init__(
        self,
        name: str,
        tools: List[BaseTool],
        vector_service = None,
        **kwargs
    ):
        """Initialize the agent with tools and configuration"""
        self.name = name
        self.tools = tools
        self.vector_service = vector_service
        self.logger = logging.getLogger(f"agent.{name}")
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        )
        
        # Initialize tool executor
        self.tool_executor = ToolExecutor(tools) if tools else None
        
        # Create agent prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "{input}")
        ])
        
        # Create workflow
        self.workflow = self._create_workflow()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Create the agent's prompt template"""
        return ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="messages"),
            ("human", "{input}")
        ])
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        tools_str = "\n".join(f"- {tool.name}: {tool.description}" for tool in self.tools)
        return f"""You are an AI assistant specialized in email processing.
You have access to these tools:

{tools_str}

Follow these steps:
1. Analyze the input and context
2. If you need more information, use an appropriate tool
3. Once you have enough information, provide a final answer

Use this format:
- To use a tool:
  Action: tool_name
  Action Input: <your input>

- To provide final answer:
  Final Answer: <your response>

Always think step-by-step and explain your reasoning."""
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self._agent_step)
        workflow.add_node("action", self._execute_action)
        workflow.add_node("process_response", self._process_response)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._route_agent_step,
            {
                "action": "action",
                "final": "process_response",
                "error": END
            }
        )
        
        # Add edge from action back to agent
        workflow.add_edge("action", "agent")
        
        # Add edge from process_response to end
        workflow.add_edge("process_response", END)
        
        return workflow.compile()
    
    async def _agent_step(self, state: AgentState) -> AgentState:
        """Execute one step of agent reasoning"""
        try:
            # Prepare messages
            messages = self.prompt.format_messages(
                messages=state.messages,
                input=self._format_input(state)
            )
            
            # Get agent's response
            response = await self.llm.ainvoke(messages)
            state.messages.append(response)
            
            # Parse the response
            parsed = self._parse_llm_response(response.content)
            
            if isinstance(parsed, AgentAction):
                state.current_action = parsed
                state.actions.append(parsed)
            elif isinstance(parsed, AgentFinish):
                state.final_answer = parsed.return_values["output"]
            
            return state
            
        except Exception as e:
            state.error = f"Agent step failed: {str(e)}"
            self.logger.error(state.error)
            return state
    
    def _route_agent_step(self, state: AgentState) -> str:
        """Route the workflow based on agent state"""
        if state.error:
            return "error"
        if state.final_answer:
            return "final"
        if state.current_action:
            return "action"
        return "error"
    
    async def _execute_action(self, state: AgentState) -> AgentState:
        """Execute the current tool action"""
        try:
            if not state.current_action or not self.tool_executor:
                state.error = "No action to execute or no tool executor"
                return state
            
            # Execute tool
            result = await self.tool_executor.ainvoke({
                "tool_name": state.current_action.tool,
                "tool_input": state.current_action.tool_input
            })
            
            # Store result
            state.action_results.append(str(result))
            state.messages.append(AIMessage(content=f"Observation: {result}"))
            state.current_action = None
            
            return state
            
        except Exception as e:
            state.error = f"Action execution failed: {str(e)}"
            self.logger.error(state.error)
            return state
    
    async def _process_response(self, state: AgentState) -> AgentState:
        """Process the final response"""
        try:
            if not state.final_answer:
                state.error = "No final answer to process"
                return state
            
            # Store the response
            state.response = state.final_answer
            
            # Add metadata
            state.metadata.update({
                "steps_taken": len(state.actions),
                "tools_used": [action.tool for action in state.actions],
                "completion_time": "now"  # You might want to add actual timestamp
            })
            
            return state
            
        except Exception as e:
            state.error = f"Response processing failed: {str(e)}"
            self.logger.error(state.error)
            return state
    
    def _format_input(self, state: AgentState) -> str:
        """Format the current state for the agent prompt"""
        parts = []
        
        if state.email_content:
            parts.append(f"Email Content: {state.email_content}")
        if state.intent:
            parts.append(f"Intent: {state.intent}")
        if state.context:
            parts.append(f"Context: {state.context}")
        
        # Add action history
        if state.actions and state.action_results:
            history = []
            for action, result in zip(state.actions, state.action_results):
                history.extend([
                    f"Action: {action.tool}({action.tool_input})",
                    f"Result: {result}"
                ])
            parts.append("Action History:\n" + "\n".join(history))
        
        return "\n\n".join(parts)
    
    def _parse_llm_response(self, response: str) -> Union[AgentAction, AgentFinish]:
        """Parse the LLM response into an action or final answer"""
        response = response.strip()
        
        if "Action:" in response:
            # Parse action and input
            action_match = re.search(r"Action: (\w+)\nAction Input: (.*?)(?:\n|$)", response, re.DOTALL)
            if action_match:
                tool = action_match.group(1).strip()
                tool_input = action_match.group(2).strip()
                return AgentAction(tool=tool, tool_input=tool_input)
        
        # If no action found, treat as final answer
        final_answer = response.replace("Final Answer:", "").strip()
        return AgentFinish(return_values={"output": final_answer})
    
    @abstractmethod
    async def process(self, state: AgentState) -> AgentResult:
        """
        Process the agent state and return results.
        Must be implemented by all concrete agent classes.
        """
        pass
    
    async def execute_with_tools(self, input_text: str, context: Optional[Dict] = None) -> AgentResult:
        """Execute the agent workflow"""
        try:
            # Create initial state
            initial_state = AgentState(
                email_content=input_text,
                metadata=context or {}
            )
            
            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            if final_state.error:
                return AgentResult(
                    success=False,
                    error=final_state.error,
                    metadata={"agent": self.name}
                )
            
            return AgentResult(
                success=True,
                data={
                    "response": final_state.response,
                    "actions": [
                        {"tool": action.tool, "input": action.tool_input}
                        for action in final_state.actions
                    ],
                    "metadata": final_state.metadata
                },
                metadata={
                    "agent": self.name,
                    "steps_taken": len(final_state.actions)
                }
            )
            
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            self.logger.error(error_msg)
            return AgentResult(
                success=False,
                error=error_msg,
                metadata={"agent": self.name}
            )

# Example usage
if __name__ == "__main__":
    import asyncio
    
    class TestAgent(BaseAgent):
        async def process(self, state: AgentState) -> AgentResult:
            result = await self.execute_with_tools(
                state.email_content or "",
                context={"test": True}
            )
            return result
    
    async def test_agent():
        agent = TestAgent(
            name="test_agent",
            tools=[
                # Add some test tools here
            ]
        )
        state = AgentState(email_content="Test email content")
        result = await agent.process(state)
        print(f"Result: {result}")
    
    # Run test
    # asyncio.run(test_agent())