"""
Query Refinement Agent: Improves and expands user queries for better research results.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import logging

logger = logging.getLogger(__name__)

class RefinedQuery(BaseModel):
    """Model for a refined query"""
    main_query: str
    sub_queries: List[str]
    keywords: List[str]
    context: Optional[str]

class QueryRefinementAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo-16k",
            temperature=0.4
        )
        
        self.refinement_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a query optimization expert. Analyze the user's query and generate improved versions with relevant sub-queries."),
            ("human", "Original query: {query}\nPlease refine this query and generate relevant sub-queries.")
        ])
        
        self.refinement_chain = LLMChain(
            llm=self.llm,
            prompt=self.refinement_prompt
        )
    
    def extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from the query"""
        # Remove common words and extract key terms
        common_words = {"what", "how", "why", "when", "where", "is", "are", "the", "in", "on", "at", "to", "for"}
        words = query.lower().split()
        keywords = [word for word in words if word not in common_words]
        return list(set(keywords))
    
    async def process_message(self, state: Dict) -> Dict:
        """Refine the user's query"""
        try:
            logger.info("Starting query refinement process")
            
            # Get query from state
            original_query = state.get("query", "")
            if not original_query:
                raise ValueError("No query provided in state")
                
            keywords = self.extract_keywords(original_query)
            
            # Generate refined queries
            refinement_response = await self.refinement_chain.ainvoke({
                "query": original_query
            })
            
            # Structure the results
            refined_query = original_query
            sub_queries = []
            
            if refinement_response.get("text"):
                # Parse the LLM response to extract refined queries
                lines = refinement_response["text"].split("\n")
                sub_queries = [line.strip() for line in lines if line.strip()]
                if sub_queries:
                    refined_query = sub_queries[0]
            
            # Update state
            state.update({
                "query": refined_query,
                "sub_queries": sub_queries,
                "keywords": keywords,
                "context": "",
                "current_agent": "query_refinement"
            })
            
            logger.info("Query refinement completed successfully")
            return state
            
        except Exception as e:
            error_msg = f"Error in query refinement: {str(e)}"
            logger.error(error_msg)
            state["errors"] = [error_msg]
            return state
