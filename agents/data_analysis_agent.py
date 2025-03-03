"""
Data Analysis Agent: Processes numerical data and generates insights from research findings.
"""
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import re
import logging

logger = logging.getLogger(__name__)

class DataPoint(BaseModel):
    """Model for a single data point"""
    value: Union[float, int, str]
    context: str
    source: str

class AnalysisResult(BaseModel):
    """Output model for data analysis"""
    trends: List[str]
    statistics: Dict[str, float]
    visualizations: List[Dict]
    insights: List[str]

class DataAnalysisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo-16k",
            temperature=0.3
        )
        
        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a data analysis expert. Extract and analyze numerical data from the provided text, identify trends, and generate insights."),
            ("human", "Text to analyze: {text}\nPlease extract numerical data and provide analysis.")
        ])
        
        self.analysis_chain = LLMChain(
            llm=self.llm,
            prompt=self.analysis_prompt
        )
    
    def extract_numerical_data(self, text: str) -> List[DataPoint]:
        """Extract numerical values with context from text"""
        # Simple pattern to find numbers with surrounding context
        pattern = r'(\d+(?:\.\d+)?(?:\s*%|\s*million|\s*billion)?)'
        matches = re.finditer(pattern, text)
        data_points = []
        
        for match in matches:
            # Get some context around the number
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()
            
            data_points.append(DataPoint(
                value=match.group(1),
                context=context,
                source="text"
            ))
        
        return data_points
    
    async def process_message(self, input_data: Dict) -> Dict:
        """Process research results and analyze numerical data"""
        try:
            logger.info("Starting data analysis process")
            
            # Combine all research results into one text
            combined_text = "\n".join([
                result.get("content", "") 
                for result in input_data.get("research_results", [])
            ])
            
            # Extract numerical data
            data_points = self.extract_numerical_data(combined_text)
            
            # Run analysis
            analysis_response = await self.analysis_chain.ainvoke({
                "text": combined_text
            })
            
            # Structure the results
            analysis_result = {
                "trends": [],
                "statistics": {},
                "insights": [],
                "data_points": [dp.dict() for dp in data_points]
            }
            
            if analysis_response.get("text"):
                # Here you would parse the LLM response and structure it
                # This is a simplified version
                analysis_result["insights"] = [analysis_response["text"]]
            
            logger.info("Data analysis completed successfully")
            return analysis_result
            
        except Exception as e:
            error_msg = f"Error in data analysis: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
