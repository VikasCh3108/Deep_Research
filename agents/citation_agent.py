"""
Citation Agent: Manages and verifies sources, formats citations, and evaluates source credibility.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Source(BaseModel):
    """Model for a source"""
    url: str
    title: str
    author: Optional[str]
    date: Optional[str]
    publisher: Optional[str]
    credibility_score: float = 0.0

class CitationResult(BaseModel):
    """Output model for citations"""
    formatted_citations: List[str]
    source_evaluations: List[Dict]
    bibliography: str

class CitationAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo-16k",
            temperature=0.2
        )
        
        self.citation_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a citation and source evaluation expert. Format citations in APA style and evaluate source credibility."),
            ("human", "Sources to process: {sources}\nPlease format citations and evaluate credibility.")
        ])
        
        self.citation_chain = LLMChain(
            llm=self.llm,
            prompt=self.citation_prompt
        )
    
    def evaluate_source_credibility(self, source: Dict) -> float:
        """Evaluate the credibility of a source based on various factors"""
        score = 0.0
        
        # Check if it's from a known reliable domain
        reliable_domains = [".edu", ".gov", ".org"]
        if any(domain in source.get("url", "").lower() for domain in reliable_domains):
            score += 0.3
            
        # Check if it has an author
        if source.get("author"):
            score += 0.2
            
        # Check if it has a recent date
        if source.get("date"):
            try:
                date = datetime.strptime(source["date"], "%Y-%m-%d")
                if (datetime.now() - date).days < 365:
                    score += 0.2
            except:
                pass
                
        # Check if it has a reputable publisher
        if source.get("publisher"):
            score += 0.3
            
        return min(score, 1.0)
    
    async def process_message(self, input_data: Dict) -> Dict:
        """Process sources and generate citations"""
        try:
            logger.info("Starting citation process")
            
            sources = []
            for result in input_data.get("research_results", []):
                source = {
                    "url": result.get("url"),
                    "title": result.get("title"),
                    "content": result.get("content"),
                    "date": result.get("date", ""),
                    "author": result.get("author", ""),
                    "publisher": result.get("publisher", "")
                }
                sources.append(source)
            
            # Evaluate source credibility
            for source in sources:
                source["credibility_score"] = self.evaluate_source_credibility(source)
            
            # Generate citations
            citation_response = await self.citation_chain.ainvoke({
                "sources": sources
            })
            
            # Structure the results
            citation_result = {
                "formatted_citations": [],
                "source_evaluations": [
                    {
                        "url": s["url"],
                        "credibility_score": s["credibility_score"]
                    }
                    for s in sources
                ],
                "bibliography": citation_response.get("text", "")
            }
            
            logger.info("Citation process completed successfully")
            return citation_result
            
        except Exception as e:
            error_msg = f"Error in citation processing: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
