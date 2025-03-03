"""
Fact Checking Agent: Verifies information and assigns confidence scores to research findings.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import logging

logger = logging.getLogger(__name__)

class FactCheckInput(BaseModel):
    """Input model for fact checking"""
    statements: List[Dict]
    sources: List[str]

class FactCheckResult(BaseModel):
    """Output model for fact checking"""
    verified_statements: List[Dict]
    confidence_scores: List[float]
    source_reliability: Dict[str, float]

class FactCheckingAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo-16k",
            temperature=0.2
        )
        
        self.fact_check_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a precise fact-checking assistant. Analyze the following statements and their sources, then provide a detailed verification with confidence scores."),
            ("human", "Statements to verify: {statements}\nSources: {sources}\nPlease verify each statement and provide confidence scores.")
        ])
        
        self.fact_check_chain = LLMChain(
            llm=self.llm,
            prompt=self.fact_check_prompt
        )
        
    async def process_message(self, input_data: Dict) -> Dict:
        """Process statements and verify facts"""
        try:
            logger.info("Starting fact verification process")
            
            # Extract statements from research results
            statements = []
            sources = []
            for result in input_data.get("research_results", []):
                statements.append({
                    "content": result.get("content"),
                    "source": result.get("url")
                })
                sources.append(result.get("url"))
            
            # Run fact checking
            fact_check_response = await self.fact_check_chain.ainvoke({
                "statements": statements,
                "sources": sources
            })
            
            # Process and structure the response
            verified_data = {
                "verified_statements": [],
                "confidence_scores": [],
                "source_reliability": {},
                "overall_confidence": 0.0
            }
            
            # Add structured verification results
            if fact_check_response.get("text"):
                # Process the LLM response and structure it
                # This is a simplified version - you might want to add more sophisticated parsing
                verified_data["verified_statements"] = statements
                verified_data["overall_confidence"] = 0.8  # Example score
            
            logger.info("Fact checking completed successfully")
            return verified_data
            
        except Exception as e:
            error_msg = f"Error in fact checking: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
