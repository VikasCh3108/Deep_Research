"""
Synthesis Agent: Processes and synthesizes collected information into coherent answers.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import create_extraction_chain, MapReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain.chains.summarize import load_summarize_chain
import logging

logger = logging.getLogger(__name__)

class SynthesisInput(BaseModel):
    """Input model for synthesis"""
    research_results: List[Dict]
    query: str
    max_tokens: int = Field(default=2000, description="Maximum tokens in the synthesized response")

class SynthesisResult(BaseModel):
    """Output model for synthesis"""
    summary: str
    key_points: List[str]
    sources: List[str]
    confidence_score: float = Field(default=0.0, description="Confidence score of the synthesis")

class SynthesisAgent:
    def __init__(self):
        # Initialize text splitter for document chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " "]
        )
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo-16k",
            temperature=0.3,
            max_tokens=1000
        )
        
        # Create summarization chain with enhanced metadata usage
        map_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a precise and analytical assistant that helps extract key information from text. Focus on extracting factual, relevant information and organizing it clearly. Pay special attention to source quality and confidence scores when evaluating information."),
            ("human", "Analyze the following text and extract the main points and facts that are relevant to the query: {query}\n\n"
                      "Text: {text}\n\n"
                      "Source Metadata:\n"
                      "- Confidence Score: {confidence_score}\n"
                      "- Source Quality: {source_quality}\n"
                      "- Importance: {importance}\n\n"
                      "Format your response in clear sections:\n"
                      "1. Key Facts: List the most important facts, prioritizing those from high-confidence sources\n"
                      "2. Supporting Details: Add relevant context, noting source credibility\n"
                      "3. Confidence Assessment:\n"
                      "   - Information Quality (0-1)\n"
                      "   - Source Credibility (0-1)\n"
                      "   - Relevance to Query (0-1)")
        ])
        
        combine_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that synthesizes information into clear and concise summaries. Your goal is to provide accurate, well-structured responses that directly answer the user's query. Prioritize information from high-confidence, authoritative sources while still considering all available data."),
            ("human", "Based on the following extracted information, provide a comprehensive answer to the query: {query}\n\n"
                      "Extracted information: {text}\n\n"
                      "Format your response EXACTLY as follows (keep the exact headings and structure):\n\n"
                      "Summary:\n[Write a clear, focused summary that directly answers the query in 2-3 paragraphs. Prioritize findings from high-confidence sources.]\n\n"
                      "Key Points:\n"
                      "- [High confidence finding 1]\n"
                      "- [High confidence finding 2]\n"
                      "- [Additional relevant finding]\n\n"
                      "Source Analysis:\n"
                      "- Primary Sources: [List high-confidence sources]\n"
                      "- Supporting Sources: [List other contributing sources]\n\n"
                      "Confidence Assessment:\n"
                      "- Overall Confidence Score: [0-1]\n"
                      "- Information Quality: [0-1]\n"
                      "- Source Diversity: [0-1]\n"
                      "- Coverage of Query: [0-1]")
        ])
        
        # Create map chain for initial document processing
        map_chain = LLMChain(llm=self.llm, prompt=map_prompt)
        
        # Create reduce chain for combining results
        reduce_chain = LLMChain(llm=self.llm, prompt=combine_prompt)
        
        # Create a StuffDocumentsChain for the reduce step
        reduce_documents_chain = StuffDocumentsChain(
            llm_chain=reduce_chain,
            document_variable_name="text"
        )
        
        # Create the final map_reduce chain
        self.chain = MapReduceDocumentsChain(
            llm_chain=map_chain,
            combine_document_chain=reduce_documents_chain,
            document_variable_name="text",
            return_intermediate_steps=True
        )
        
    def _prepare_documents(self, research_results: List[Dict]) -> List[Document]:
        """
        Convert research results into LangChain documents for processing.
        
        Args:
            research_results (List[Dict]): List of research results from Tavily
            
        Returns:
            List[Document]: List of LangChain documents
        """
        documents = []
        for result in research_results:
            if not isinstance(result, dict):
                logger.warning(f"Skipping invalid result: {result}")
                continue
                
            # Create document with enhanced metadata
            try:
                # Calculate document weight based on confidence and relevance
                confidence = result.get('confidence_score', 0.5)
                relevance = result.get('relevance_score', 0.5)
                source_quality = result.get('source_quality', {})
                
                # Weighted importance calculation
                importance = (
                    confidence * 0.4 +  # Confidence in source/content
                    relevance * 0.3 +   # Relevance to query
                    source_quality.get('domain_authority', 1.0) * 0.15 +  # Domain authority
                    source_quality.get('content_quality', 1.0) * 0.1 +   # Content quality
                    source_quality.get('recency', 1.0) * 0.05            # Recency
                )
                
                doc = Document(
                    page_content=result.get('content', ''),
                    metadata={
                        'title': result.get('title', 'Untitled'),
                        'url': result.get('url', ''),
                        'relevance_score': relevance,
                        'confidence_score': confidence,
                        'importance': importance,
                        'source_quality': source_quality
                    }
                )
                documents.append(doc)
            except Exception as e:
                logger.error(f"Error creating document: {str(e)}")
                continue
        
        if not documents:
            logger.warning("No valid documents created from research results")
            return []
        
        # Split documents into chunks
        try:
            split_docs = []
            for doc in documents:
                splits = self.text_splitter.split_documents([doc])
                split_docs.extend(splits)
            
            logger.info(f"Created {len(split_docs)} document chunks from {len(documents)} research results")
            return split_docs
        except Exception as e:
            logger.error(f"Error splitting documents: {str(e)}")
            return documents  # Return original documents if splitting fails
    
    def _parse_chain_output(self, output: str) -> Dict[str, Any]:
        """
        Parse the chain output into structured format.
        
        Args:
            output (str): Raw output from the chain
            
        Returns:
            Dict[str, Any]: Structured output
        """
        try:
            # Initialize default values
            result = {
                'summary': '',
                'key_points': [],
                'confidence_score': 0.0
            }
            
            # Split into sections and parse
            sections = output.split('\n\n')
            current_section = None
            
            for section in sections:
                section = section.strip()
                
                if section.startswith('Summary:'):
                    current_section = 'summary'
                    result['summary'] = section.replace('Summary:', '').strip()
                elif section.startswith('Key Points:'):
                    current_section = 'key_points'
                    points = section.replace('Key Points:', '').strip().split('\n')
                    result['key_points'] = [p.strip('- ').strip() for p in points if p.strip() and not p.strip().startswith('Key Points:')]
                elif section.startswith('Confidence Score:'):
                    try:
                        score_str = section.replace('Confidence Score:', '').strip()
                        if score_str and score_str[0].isdigit():
                            score = float(score_str)
                            result['confidence_score'] = min(max(score, 0.0), 1.0)
                    except ValueError:
                        logger.warning(f"Could not parse confidence score from: {section}")
                elif current_section == 'summary' and section:
                    # Append to existing summary
                    result['summary'] += '\n' + section
                elif current_section == 'key_points' and section:
                    # Add as new key points
                    points = section.split('\n')
                    result['key_points'].extend([p.strip('- ').strip() for p in points if p.strip()])
            
            # Clean up the results
            result['summary'] = result['summary'].strip()
            result['key_points'] = [p for p in result['key_points'] if p]
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing chain output: {str(e)}")
            return {
                'summary': output,
                'key_points': [],
                'confidence_score': 0.0
            }
    
    async def process_message(self, message: Dict) -> Dict:
        """
        Process research results and synthesize an answer with enhanced metadata handling.
        
        Args:
            message (Dict): Input message containing research results and query
            
        Returns:
            Dict: Synthesized results with confidence metrics
        """
        try:
            # Extract research results and query
            if not isinstance(message, dict):
                raise ValueError("Message must be a dictionary")
                
            research_results = message.get('research_results', [])
            query = message.get('query', '')
            
            if not research_results or not query:
                return SynthesisResult(
                    summary="No research results or query provided.",
                    key_points=[],
                    sources=[],
                    confidence_score=0.0
                ).dict()
            
            # Create input data
            input_data = SynthesisInput(
                research_results=research_results,
                query=query
            )
            
            # Prepare documents with metadata
            docs = self._prepare_documents(input_data.research_results)
            
            if not docs:
                return SynthesisResult(
                    summary="No relevant information found.",
                    key_points=[],
                    sources=[],
                    confidence_score=0.0
                ).dict()
            
            # Sort documents by importance score
            docs.sort(key=lambda x: x.metadata.get('importance', 0), reverse=True)
            
            # Run summarization chain with metadata
            try:
                chain_output = await self.chain.arun(
                    input_documents=docs,
                    query=input_data.query
                )
            except Exception as e:
                logger.error(f"Error running chain: {str(e)}")
                raise Exception(f"Chain execution failed: {str(e)}")
            
            # Parse chain output
            result = self._parse_chain_output(chain_output)
            
            # Calculate source quality metrics
            source_metrics = {
                'high_quality_sources': 0,
                'medium_quality_sources': 0,
                'low_quality_sources': 0
            }
            
            sources = []
            for doc in docs:
                importance = doc.metadata.get('importance', 0)
                url = doc.metadata.get('url')
                
                if url and url not in sources:
                    sources.append(url)
                    if importance > 0.7:
                        source_metrics['high_quality_sources'] += 1
                    elif importance > 0.4:
                        source_metrics['medium_quality_sources'] += 1
                    else:
                        source_metrics['low_quality_sources'] += 1
            
            # Calculate overall source quality
            total_sources = len(sources)
            if total_sources > 0:
                source_quality = (
                    source_metrics['high_quality_sources'] * 1.0 +
                    source_metrics['medium_quality_sources'] * 0.6 +
                    source_metrics['low_quality_sources'] * 0.3
                ) / total_sources
            else:
                source_quality = 0.0
            
            # Adjust confidence score based on source quality
            confidence_score = min(1.0, (
                result.get('confidence_score', 0.5) * 0.7 +
                source_quality * 0.3
            ))
            
            return SynthesisResult(
                summary=result.get('summary', ''),
                key_points=result.get('key_points', []),
                sources=sources,
                confidence_score=confidence_score
            ).dict()
            
        except Exception as e:
            logger.error(f"Error in synthesis: {str(e)}")
            return SynthesisResult(
                summary=f"Error during synthesis: {str(e)}",
                key_points=[],
                sources=[],
                confidence_score=0.0
            ).dict()

    def _extract_key_points(self, content: str) -> List[str]:
        """
        Extract key points from synthesized content.
        
        Args:
            content (str): Synthesized content
            
        Returns:
            List[str]: List of key points
        """
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        # Extract main points (this is a simple implementation)
        key_points = []
        for para in paragraphs:
            if para.strip():
                # Take first sentence of each paragraph as a key point
                point = para.split('. ')[0].strip()
                if point and len(point) > 20:  # Minimum length threshold
                    key_points.append(point)
                    
        return key_points[:5]  # Return top 5 key points
        
    async def synthesize(self, input_data: SynthesisInput) -> SynthesisResult:
        """
        Synthesize research results into a coherent response.
        
        Args:
            input_data (SynthesisInput): Input data containing research results
            
        Returns:
            SynthesisResult: Synthesized result with summary and key points
        """
        try:
            # Prepare documents
            documents = self._prepare_documents(input_data.research_results)
            
            # Sort documents by relevance score
            documents.sort(key=lambda x: x.metadata['relevance_score'], reverse=True)
            
            # Combine content from most relevant documents
            combined_content = "\n\n".join([doc.page_content for doc in documents[:3]])
            
            # Extract key points
            key_points = self._extract_key_points(combined_content)
            
            # Create summary (simplified version)
            summary = combined_content[:input_data.max_tokens]
            
            # Get sources
            sources = []
            for doc in documents[:3]:
                url = doc.metadata.get('url')
                if url and url not in sources:
                    sources.append(url)
            
            return SynthesisResult(
                summary=summary,
                key_points=key_points,
                sources=sources
            )
            
        except Exception as e:
            raise Exception(f"Synthesis error: {str(e)}")
            
    async def process_message(self, message: Dict) -> Dict:
        """
        Process incoming messages and return synthesized results.
        
        Args:
            message (Dict): Input message containing research results
            
        Returns:
            Dict: Synthesized results and status
        """
        input_data = SynthesisInput(**message)
        result = await self.synthesize(input_data)
        
        return {
            "status": "success",
            "synthesis": result.dict()
        }
