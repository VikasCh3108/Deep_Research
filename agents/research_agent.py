"""
Research Agent: Responsible for web crawling and information gathering using Tavily API.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseLLM
from tavily import TavilyClient
from dotenv import load_dotenv
import os
import logging
import sys
import json
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

load_dotenv()

class ResearchQuery(BaseModel):
    """Research query model"""
    query: str = Field(..., description="The research query to investigate")
    max_results: int = Field(default=5, description="Maximum number of results to return")
    search_depth: str = Field(default="basic", description="Search depth: basic, moderate, or deep")

class ResearchResult(BaseModel):
    """Research result model"""
    title: str
    url: str
    content: str
    relevance_score: float

class ResearchAgent:
    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")
        api_key = api_key.strip()  # Remove any whitespace
        logger.info(f"Initializing TavilyClient with API key: {api_key[:8]}...")
        self.tavily_client = TavilyClient(api_key=api_key)
        
        # Test API key
        try:
            test_results = self.tavily_client.search(query="test", search_depth="basic")
            if not isinstance(test_results, dict) or 'results' not in test_results:
                raise ValueError("Invalid API response format")
            logger.info("Successfully tested Tavily API connection")
        except Exception as e:
            logger.error(f"Failed to test Tavily API: {str(e)}")
            raise ValueError("Failed to initialize Tavily API client") from e
        
    async def research(self, query: ResearchQuery) -> List[Dict]:
        """
        Conduct research based on the provided query using Tavily API.
        Includes URL validation and security checks.
        
        Args:
            query (ResearchQuery): The research query parameters
            
        Returns:
            List[Dict]: List of research results
        """
        # Import URL validator
        from middleware.url_security import url_validator
        try:
            # Log the request parameters
            request_params = {
                "query": query.query,
                "search_depth": "advanced",  # Use advanced search for better results
                "max_results": query.max_results,
                "include_answer": True,
                "include_raw_content": False,
                "topic": "general",
                "include_domains": [],
                "exclude_domains": []
            }
            logger.info(f"Making Tavily API request for query: {query.query}")
            
            # Execute search using asyncio to run the sync method
            import asyncio
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                None,
                lambda: self.tavily_client.search(**request_params)
            )
            
            if not isinstance(search_results, dict):
                logger.error(f"Unexpected API response format: {type(search_results)}")
                return []
            
            # Extract and format results with confidence scoring
            results = []
            for result in search_results.get('results', []):
                if not isinstance(result, dict):
                    continue
                    
                content = result.get('content', '')
                if not content:
                    continue
                
                # Calculate confidence score based on multiple factors
                base_score = float(result.get('score', 0.0))
                
                # Factor 1: Domain authority (educational/research domains get higher scores)
                url = result.get('url', '')
                domain_boost = 1.0
                if any(domain in url.lower() for domain in ['.edu', '.gov', '.org', 'arxiv.org', 'research.', 'science.']):
                    domain_boost = 1.2
                elif any(domain in url.lower() for domain in ['blog.', 'medium.com']):
                    domain_boost = 0.8
                
                # Factor 2: Content quality indicators
                content_boost = 1.0
                if any(term in content.lower() for term in ['research', 'study', 'published', 'paper', 'journal']):
                    content_boost += 0.1
                if any(term in content.lower() for term in ['experiment', 'data', 'analysis', 'results']):
                    content_boost += 0.1
                
                # Factor 3: Recency (if available)
                recency_boost = 1.0
                if 'published_date' in result:
                    try:
                        from datetime import datetime
                        pub_date = datetime.strptime(result['published_date'], '%Y-%m-%d')
                        days_old = (datetime.now() - pub_date).days
                        if days_old < 30:  # Last month
                            recency_boost = 1.2
                        elif days_old < 180:  # Last 6 months
                            recency_boost = 1.1
                    except:
                        pass
                
                # Calculate final confidence score
                confidence_score = min(1.0, base_score * domain_boost * content_boost * recency_boost)
                
                # Validate URL
                url = result.get('url', '')
                is_safe, reason = await url_validator.validate_and_check_url(url)
                
                if not is_safe:
                    logger.warning(f"Skipping unsafe URL {url}: {reason}")
                    continue
                    
                # Sanitize URL
                safe_url = url_validator.sanitize_url(url)
                
                results.append({
                    'title': result.get('title', 'Untitled'),
                    'url': safe_url,
                    'content': content,
                    'relevance_score': base_score,
                    'confidence_score': confidence_score,
                    'source_quality': {
                        'domain_authority': domain_boost,
                        'content_quality': content_boost,
                        'recency': recency_boost
                    },
                    'security_verified': True
                })
            
            # Add the Tavily answer if available and not None
            answer = search_results.get('answer')
            if answer and isinstance(answer, str) and answer.strip():
                results.append({
                    'title': 'Tavily Answer',
                    'url': '',
                    'content': answer,
                    'relevance_score': 1.0  # Give highest relevance to Tavily's answer
                })
            
            # Return results only if we have some
            if results:
                logger.info(f"Found {len(results)} results from Tavily API")
                return results
            else:
                logger.warning("No valid results found from Tavily API")
                return []
            
        except Exception as e:
            logger.error(f"Error in research: {str(e)}")
            logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
            return []  # Return empty list instead of raising to avoid workflow interruption
            
    async def process_message(self, state: Dict) -> Dict:
        """
        Process incoming messages and return research results.
        
        Args:
            state (Dict): Current workflow state
            
        Returns:
            Dict: Updated workflow state
        """
        try:
            # Get query from state
            query = state.get('query', '')
            if not query:
                raise ValueError("No query provided in state")
            
            # Create research query with advanced search
            research_query = ResearchQuery(
                query=query,
                max_results=10,
                search_depth='advanced'
            )
            
            # Execute research
            results = await self.research(research_query)
            
            # Return early if no results
            if not results:
                return {
                    "status": "error",
                    "research_results": [],
                    "errors": ["No research results found"]
                }
            
            # Convert score to relevance_score for compatibility
            for result in results:
                if 'score' in result:
                    result['relevance_score'] = result.pop('score')
            
            # Return successful state
            return {
                "status": "success",
                "research_results": results,
                "current_agent": "fact_check"
            }
            
        except Exception as e:
            error_msg = f"Error in process_message: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
            return {
                "status": "error",
                "research_results": [],
                "errors": [error_msg]
            }

