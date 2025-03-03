"""
Code Analysis Agent: Processes code-related queries and analyzes code snippets from research.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import re
import logging

logger = logging.getLogger(__name__)

class CodeSnippet(BaseModel):
    """Model for a code snippet"""
    code: str
    language: str
    source: str
    explanation: Optional[str]

class CodeAnalysisResult(BaseModel):
    """Output model for code analysis"""
    snippets: List[CodeSnippet]
    explanations: List[str]
    suggestions: List[str]
    references: List[str]

class CodeAnalysisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo-16k",
            temperature=0.2
        )
        
        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a code analysis expert. Analyze code snippets, provide explanations, and suggest improvements."),
            ("human", "Code to analyze: {code}\nContext: {context}\nPlease analyze this code and provide explanations.")
        ])
        
        self.analysis_chain = LLMChain(
            llm=self.llm,
            prompt=self.analysis_prompt
        )
    
    def extract_code_snippets(self, text: str) -> List[CodeSnippet]:
        """Extract code snippets from text"""
        # Simple pattern to find code blocks
        code_block_pattern = r'```(\w+)?\n(.*?)\n```'
        matches = re.finditer(code_block_pattern, text, re.DOTALL)
        
        snippets = []
        for match in matches:
            language = match.group(1) or "unknown"
            code = match.group(2).strip()
            
            snippets.append(CodeSnippet(
                code=code,
                language=language,
                source="research_results",
                explanation=""
            ))
        
        return snippets
    
    async def process_message(self, input_data: Dict) -> Dict:
        """Process and analyze code snippets"""
        try:
            logger.info("Starting code analysis process")
            
            # Extract code snippets from research results
            all_snippets = []
            for result in input_data.get("research_results", []):
                content = result.get("content", "")
                snippets = self.extract_code_snippets(content)
                all_snippets.extend(snippets)
            
            analysis_results = []
            for snippet in all_snippets:
                # Analyze each snippet
                analysis_response = await self.analysis_chain.ainvoke({
                    "code": snippet.code,
                    "context": input_data.get("query", "")
                })
                
                if analysis_response.get("text"):
                    snippet.explanation = analysis_response["text"]
                    analysis_results.append(snippet.dict())
            
            # Structure the results
            code_analysis_result = {
                "snippets": analysis_results,
                "explanations": [s["explanation"] for s in analysis_results if s.get("explanation")],
                "suggestions": [],  # Would be populated based on analysis
                "references": []    # Would include documentation links etc.
            }
            
            logger.info("Code analysis completed successfully")
            return code_analysis_result
            
        except Exception as e:
            error_msg = f"Error in code analysis: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
