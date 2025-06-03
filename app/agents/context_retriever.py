"""
Context Retrieval Agent for finding relevant information from vector database.
Retrieves contextual information based on email content and intent.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from langchain.tools import BaseTool, tool
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb
from pydantic import BaseModel, Field

from .base_agent import BaseAgent, AgentState, AgentResult

logger = logging.getLogger(__name__)


class RetrievalResult(BaseModel):
    """Structured result for context retrieval"""
    contexts: List[str] = Field(description="Retrieved context chunks")
    sources: List[str] = Field(description="Source documents for contexts") 
    scores: List[float] = Field(description="Relevance scores for each context")
    total_contexts: int = Field(description="Total number of contexts retrieved")
    query_expansion: List[str] = Field(default_factory=list, description="Expanded query terms")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional retrieval metadata")


class VectorSearchTool(BaseTool):
    """Tool for searching the vector database"""
    
    name = "vector_search"
    description = "Search vector database for relevant context based on query"
    vector_store: Any = Field(description="Vector store instance")
    
    def __init__(self, vector_store: Any, **kwargs):
        """Initialize the tool with a vector store"""
        super().__init__(**kwargs)
        self.vector_store = vector_store
    
    def _run(self, query: str, k: int = 5, filter_dict: Optional[Dict] = None) -> Dict:
        """Search vector database for relevant documents"""
        try:
            # Perform similarity search with scores
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_dict
            )
            
            contexts = []
            sources = []
            scores = []
            
            for doc, score in results:
                contexts.append(doc.page_content)
                sources.append(doc.metadata.get('source', 'Unknown'))
                scores.append(float(score))
            
            return {
                "contexts": contexts,
                "sources": sources,
                "scores": scores,
                "total_results": len(results)
            }
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            return {
                "contexts": [],
                "sources": [],
                "scores": [],
                "total_results": 0,
                "error": str(e)
            }


class QueryExpansionTool(BaseTool):
    """Tool for expanding search queries to improve retrieval"""
    
    name = "query_expander"
    description = "Expand search queries with synonyms and related terms"
    llm: Any = Field(description="Language model for query expansion")
    expansion_prompt: PromptTemplate = Field(default_factory=lambda: PromptTemplate(
        input_variables=["original_query", "intent", "context"],
        template="""
Expand the following search query to improve information retrieval.
Add relevant synonyms, related terms, and alternative phrasings.

Original Query: {original_query}
Email Intent: {intent}
Additional Context: {context}

Generate 3-5 alternative query formulations that would help find relevant information:

1. Original: {original_query}
2. 
3. 
4. 
5. 

Only provide the expanded queries, one per line, without numbering.
"""
    ), description="Prompt template for query expansion")
    
    def __init__(self, llm: Any, **kwargs):
        """Initialize the tool with a language model"""
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, query: str, intent: str = "", context: str = "") -> Dict:
        """Expand query terms for better retrieval"""
        try:
            prompt = self.expansion_prompt.format(
                original_query=query,
                intent=intent or "general",
                context=context or "no additional context"
            )
            
            response = self.llm.invoke(prompt)
            
            # Parse expanded queries
            lines = response.content.strip().split('\n')
            expanded_queries = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith(('1.', '2.', '3.', '4.', '5.')):
                    # Remove numbering if present
                    if '. ' in line:
                        line = line.split('. ', 1)[1]
                    expanded_queries.append(line)
            
            return {
                "original_query": query,
                "expanded_queries": expanded_queries[:5],  # Limit to 5
                "total_expansions": len(expanded_queries)
            }
            
        except Exception as e:
            logger.error(f"Query expansion failed: {str(e)}")
            return {
                "original_query": query,
                "expanded_queries": [query],  # Fallback to original
                "total_expansions": 1,
                "error": str(e)
            }


class ContextFilterTool(BaseTool):
    """Tool for filtering and ranking retrieved contexts"""
    
    name = "context_filter"
    description = "Filter and rank contexts based on relevance and intent"
    llm: Any = Field(description="Language model for context filtering")
    relevance_prompt: PromptTemplate = Field(default_factory=lambda: PromptTemplate(
        input_variables=["email_content", "intent", "context", "original_query"],
        template="""
Evaluate the relevance of the following context to the email query.

Email Content: {email_content}
Email Intent: {intent}
Original Query: {original_query}

Context to Evaluate:
{context}

Rate the relevance on a scale of 1-10 where:
1-3: Not relevant or misleading
4-6: Somewhat relevant but not directly helpful
7-8: Relevant and helpful
9-10: Highly relevant and directly addresses the query

Provide only the numeric score (no explanation needed).
"""
    ), description="Prompt template for relevance scoring")
    
    def __init__(self, llm: Any, **kwargs):
        """Initialize the tool with a language model"""
        super().__init__(**kwargs)
        self.llm = llm
    
    def _run(self, contexts: List[str], email_content: str, intent: str, original_query: str) -> Dict:
        """Filter and rank contexts by relevance"""
        try:
            scored_contexts = []
            
            for i, context in enumerate(contexts):
                try:
                    prompt = self.relevance_prompt.format(
                        email_content=email_content[:500],  # Limit length
                        intent=intent,
                        context=context[:1000],  # Limit context length
                        original_query=original_query
                    )
                    
                    response = self.llm.invoke(prompt)
                    
                    # Extract numeric score
                    score_text = response.content.strip()
                    try:
                        score = float(score_text)
                        score = max(1, min(10, score))  # Clamp to 1-10 range
                    except ValueError:
                        score = 5.0  # Default score if parsing fails
                    
                    scored_contexts.append({
                        "context": context,
                        "score": score,
                        "index": i
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to score context {i}: {str(e)}")
                    scored_contexts.append({
                        "context": context,
                        "score": 5.0,  # Default score
                        "index": i
                    })
            
            # Sort by score (descending)
            scored_contexts.sort(key=lambda x: x["score"], reverse=True)
            
            # Filter contexts with score >= 6
            filtered_contexts = [
                ctx for ctx in scored_contexts if ctx["score"] >= 6.0
            ]
            
            return {
                "filtered_contexts": [ctx["context"] for ctx in filtered_contexts],
                "scores": [ctx["score"] for ctx in filtered_contexts],
                "original_indices": [ctx["index"] for ctx in filtered_contexts],
                "total_filtered": len(filtered_contexts),
                "avg_score": sum(ctx["score"] for ctx in filtered_contexts) / len(filtered_contexts) if filtered_contexts else 0
            }
            
        except Exception as e:
            logger.error(f"Context filtering failed: {str(e)}")
            return {
                "filtered_contexts": contexts,  # Return original contexts
                "scores": [5.0] * len(contexts),
                "original_indices": list(range(len(contexts))),
                "total_filtered": len(contexts),
                "avg_score": 5.0,
                "error": str(e)
            }


class ContextRetrieverAgent(BaseAgent):
    """
    Agent specialized in retrieving relevant context from vector database.
    Uses multiple strategies for comprehensive information retrieval.
    """
    
    def __init__(self, vector_service, **kwargs):
        """
        Initialize the context retriever agent.
        
        Args:
            vector_service: VectorService instance
            **kwargs: Additional arguments for base agent
        """
        # Initialize tools
        tools = [
            VectorSearchTool(vector_store=vector_service.collection),
            QueryExpansionTool(llm=kwargs.get('llm')),
            ContextFilterTool(llm=kwargs.get('llm'))
        ]
        
        super().__init__(
            name="context_retriever",
            tools=tools,
            vector_service=vector_service,
            **kwargs
        )
        
        # Store vector service reference
        self.vector_service = vector_service
        
        # Configuration
        self.max_contexts = 10
        self.min_score_threshold = 0.7
        self.max_context_length = 1000
        
        # For compatibility with existing methods
        self.vector_store = vector_service.collection
        self.embeddings = vector_service.embedding_function
    
    async def process(self, state: AgentState) -> AgentResult:
        """
        Retrieve relevant context based on email content and intent.
        
        Args:
            state: Current agent state
            
        Returns:
            AgentResult with retrieved context information
        """
        try:
            if not state.email_content:
                return AgentResult(
                    success=False,
                    error="No email content provided for context retrieval"
                )
            
            # Step 1: Generate search query from email content
            search_query = await self._generate_search_query(state)
            
            # Step 2: Expand query for better retrieval
            expanded_queries = await self._expand_query(search_query, state)
            
            # Step 3: Perform multi-query retrieval
            all_contexts = []
            all_sources = []
            all_scores = []
            
            for query in expanded_queries:
                search_results = await self._search_vector_db(
                    query, 
                    intent_filter=state.intent
                )
                
                if search_results["contexts"]:
                    all_contexts.extend(search_results["contexts"])
                    all_sources.extend(search_results["sources"])
                    all_scores.extend(search_results["scores"])
            
            # Step 4: Deduplicate and filter contexts
            unique_contexts = await self._deduplicate_contexts(
                all_contexts, all_sources, all_scores
            )
            
            # Step 5: Rank and filter by relevance
            filtered_results = await self._filter_contexts(
                unique_contexts["contexts"],
                state.email_content,
                state.intent or "general",
                search_query
            )
            
            # Step 6: Format final results
            final_contexts = filtered_results["contexts"][:self.max_contexts]
            final_sources = unique_contexts["sources"][:len(final_contexts)]
            final_scores = filtered_results["scores"][:len(final_contexts)]
            
            # Log retrieval statistics
            self.logger.info(
                f"Retrieved {len(final_contexts)} contexts from {len(expanded_queries)} queries"
            )
            
            return AgentResult(
                success=True,
                data={
                    "contexts": final_contexts,
                    "sources": final_sources,
                    "scores": final_scores,
                    "total_contexts": len(final_contexts),
                    "query_expansion": expanded_queries,
                    "search_query": search_query,
                    "retrieval_stats": {
                        "total_retrieved": len(all_contexts),
                        "after_deduplication": len(unique_contexts["contexts"]),
                        "after_filtering": len(filtered_results["contexts"]),
                        "final_count": len(final_contexts)
                    }
                },
                metadata={
                    "agent": self.name,
                    "retrieval_method": "multi_query_with_filtering",
                    "avg_relevance_score": sum(final_scores) / len(final_scores) if final_scores else 0
                }
            )
            
        except Exception as e:
            error_msg = f"Context retrieval failed: {str(e)}"
            self.logger.error(error_msg)
            return AgentResult(
                success=False,
                error=error_msg,
                metadata={"agent": self.name}
            )
    
    async def _generate_search_query(self, state: AgentState) -> str:
        """Generate search query from email content"""
        try:
            # Extract key phrases and entities from email
            email_content = state.email_content
            
            # Simple extraction - can be enhanced with NER
            query_prompt = PromptTemplate(
                input_variables=["email_content", "intent"],
                template="""
Extract the main topics and key information from this email to create a search query.
Focus on the core question or issue that needs to be addressed.

Email Content: {email_content}
Intent: {intent}

Generate a concise search query (3-8 words) that would help find relevant information:
"""
            )
            
            prompt = query_prompt.format(
                email_content=email_content[:1000],
                intent=state.intent or "general inquiry"
            )
            
            response = await self.llm.ainvoke(prompt)
            search_query = response.content.strip()
            
            # Fallback to simple keyword extraction
            if not search_query or len(search_query) < 3:
                words = email_content.lower().split()
                # Remove common words
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their'}
                keywords = [word for word in words if word not in stop_words and len(word) > 3]
                search_query = ' '.join(keywords[:5])
            
            return search_query
            
        except Exception as e:
            self.logger.error(f"Query generation failed: {str(e)}")
            # Fallback to subject or truncated content
            if state.subject:
                return state.subject
            return state.email_content[:50]
    
    async def _expand_query(self, original_query: str, state: AgentState) -> List[str]:
        """Expand query using the query expansion tool"""
        try:
            expansion_tool = QueryExpansionTool(llm=self.llm)
            expansion_result = expansion_tool._run(
                query=original_query,
                intent=state.intent or "",
                context=state.subject or ""
            )
            
            queries = [original_query] + expansion_result.get("expanded_queries", [])
            return list(dict.fromkeys(queries))  # Remove duplicates while preserving order
            
        except Exception as e:
            self.logger.error(f"Query expansion failed: {str(e)}")
            return [original_query]
    
    async def _search_vector_db(self, query: str, intent_filter: Optional[str] = None) -> Dict:
        """Search vector database with optional intent filtering"""
        try:
            search_tool = VectorSearchTool(vector_store=self.vector_store)
            
            # Prepare filter based on intent
            filter_dict = None
            if intent_filter:
                filter_dict = {"intent": intent_filter}
            
            search_results = search_tool._run(
                query=query,
                k=self.max_contexts,
                filter_dict=filter_dict
            )
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {str(e)}")
            return {"contexts": [], "sources": [], "scores": [], "total_results": 0}
    
    async def _deduplicate_contexts(
        self, 
        contexts: List[str], 
        sources: List[str], 
        scores: List[float]
    ) -> Dict:
        """Remove duplicate contexts while preserving best scores"""
        try:
            seen_contexts = {}
            unique_contexts = []
            unique_sources = []
            unique_scores = []
            
            for i, context in enumerate(contexts):
                # Use first 100 characters as deduplication key
                context_key = context[:100].strip()
                
                if context_key not in seen_contexts:
                    seen_contexts[context_key] = len(unique_contexts)
                    unique_contexts.append(context)
                    unique_sources.append(sources[i] if i < len(sources) else "Unknown")
                    unique_scores.append(scores[i] if i < len(scores) else 0.5)
                else:
                    # Keep the one with higher score
                    existing_idx = seen_contexts[context_key]
                    if i < len(scores) and existing_idx < len(unique_scores):
                        if scores[i] > unique_scores[existing_idx]:
                            unique_contexts[existing_idx] = context
                            unique_sources[existing_idx] = sources[i]
                            unique_scores[existing_idx] = scores[i]
            
            return {
                "contexts": unique_contexts,
                "sources": unique_sources,
                "scores": unique_scores
            }
            
        except Exception as e:
            self.logger.error(f"Context deduplication failed: {str(e)}")
            return {"contexts": contexts, "sources": sources, "scores": scores}
    
    async def _filter_contexts(
        self, 
        contexts: List[str], 
        email_content: str, 
        intent: str, 
        query: str
    ) -> Dict:
        """Filter contexts by relevance using LLM scoring"""
        try:
            filter_tool = ContextFilterTool(llm=self.llm)
            
            filter_results = filter_tool._run(
                contexts=contexts,
                email_content=email_content,
                intent=intent,
                original_query=query
            )
            
            return {
                "contexts": filter_results["filtered_contexts"],
                "scores": filter_results["scores"]
            }
            
        except Exception as e:
            self.logger.error(f"Context filtering failed: {str(e)}")
            return {"contexts": contexts, "scores": [5.0] * len(contexts)}
    
    async def validate_input(self, state: AgentState) -> bool:
        """Validate input state for context retrieval"""
        if not state.email_content:
            self.logger.error("No email content provided for context retrieval")
            return False
        
        if not self.vector_store:
            self.logger.error("Vector store not initialized")
            return False
        
        return True
    
    def get_retrieval_stats(self) -> Dict:
        """Get statistics about the vector database"""
        try:
            # Get collection info from Chroma
            collection = self.vector_store._collection
            return {
                "total_documents": collection.count(),
                "collection_name": collection.name,
                "embedding_dimension": len(self.embeddings.embed_query("test"))
            }
        except Exception as e:
            self.logger.error(f"Failed to get retrieval stats: {str(e)}")
            return {"error": str(e)}
    
    async def add_context_to_db(self, texts: List[str], metadata: List[Dict], sources: List[str]) -> bool:
        """Add new contexts to the vector database"""
        try:
            # Prepare documents
            documents = []
            for i, text in enumerate(texts):
                doc_metadata = metadata[i] if i < len(metadata) else {}
                doc_metadata["source"] = sources[i] if i < len(sources) else f"doc_{i}"
                
                documents.append(Document(
                    page_content=text,
                    metadata=doc_metadata
                ))
            
            # Add to vector store
            self.vector_store.add_documents(documents)
            
            self.logger.info(f"Added {len(documents)} contexts to vector database")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add contexts to database: {str(e)}")
            return False


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from langchain_community.vectorstores import Chroma
    from langchain.embeddings import OpenAIEmbeddings
    
    async def test_context_retriever():
        # Initialize vector store (would normally be loaded from persistent storage)
        embeddings = OpenAIEmbeddings()
        vector_store = Chroma(
            collection_name="email_context",
            embedding_function=embeddings,
            persist_directory="./data/vector_db"
        )
        
        # Add some test documents
        test_docs = [
            "Our return policy allows returns within 30 days of purchase with original receipt.",
            "For technical support, please provide your product serial number and error message.",
            "Shipping typically takes 3-5 business days for standard delivery.",
            "To reset your password, click the 'Forgot Password' link on the login page."
        ]
        
        retriever = ContextRetrieverAgent(
            vector_service=vector_store
        )
        
        # Test retrieval
        test_state = AgentState(
            email_content="I need help with returning my recent purchase. How long do I have to return it?",
            intent="question",
            subject="Return Policy Question"
        )
        
        result = await retriever.process(test_state)
        print(f"Retrieval result: {result.data}")
    
    # Run test
    # asyncio.run(test_context_retriever())