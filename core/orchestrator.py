"""Orchestrator: Manages the workflow between Research and Synthesis agents using LangGraph."""
from typing import Dict, List, Optional, Union, Any, Tuple
from typing_extensions import TypedDict
from langgraph.graph import END, StateGraph
from agents.research_agent import ResearchAgent
from agents.synthesis_agent import SynthesisAgent
from agents.fact_checking_agent import FactCheckingAgent
from agents.data_analysis_agent import DataAnalysisAgent
from agents.code_analysis_agent import CodeAnalysisAgent
from agents.citation_agent import CitationAgent
from agents.query_refinement_agent import QueryRefinementAgent
import logging

logger = logging.getLogger(__name__)

class AgentState(TypedDict, total=False):
    """State for the research workflow."""
    query: str
    refined_query: Optional[str]
    sub_queries: List[str]
    research_results: List[Dict]
    synthesis_result: Optional[Dict]
    fact_check_result: Optional[Dict]
    data_analysis_result: Optional[Dict]
    citations: Optional[Dict]
    code_analysis_result: Optional[Dict]
    errors: List[str]
    current_agent: str

class ResearchNode:
    """Node for performing research."""
    def __init__(self, research_agent: ResearchAgent):
        self.research_agent = research_agent

    async def __call__(self, state: AgentState) -> Union[AgentState, str]:
        """Execute research step."""
        try:
            logger.info(f"Starting research for query: {state['query']}")
            results = await self.research_agent.process_message({"query": state['query']})
            
            if not results.get("research_results"):
                state["errors"].append("No research results found")
                return state
            
            state["research_results"] = results["research_results"]
            state["current_agent"] = "fact_check"
            return state
            
        except Exception as e:
            error_msg = f"Error in research step: {str(e)}"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            return state

class QueryRefinementNode:
    """Node for refining user queries."""
    def __init__(self, query_agent: QueryRefinementAgent):
        self.query_agent = query_agent

    async def __call__(self, state: AgentState) -> Union[AgentState, str]:
        """Execute query refinement step."""
        try:
            logger.info(f"Starting query refinement for: {state['query']}")
            refinement = await self.query_agent.process_message({"query": state['query']})
            
            state["refined_query"] = refinement.get("refined_query")
            state["sub_queries"] = refinement.get("sub_queries", [])
            state["current_agent"] = "research"
            return state
            
        except Exception as e:
            error_msg = f"Error in query refinement: {str(e)}"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            return state

class FactCheckNode:
    """Node for fact checking research results."""
    def __init__(self, fact_checking_agent: FactCheckingAgent):
        self.fact_checking_agent = fact_checking_agent

    async def __call__(self, state: AgentState) -> Union[AgentState, str]:
        """Execute fact checking step."""
        try:
            logger.info("Starting fact checking of research results")
            fact_check = await self.fact_checking_agent.process_message({
                "research_results": state["research_results"],
                "query": state["query"]
            })
            
            state["fact_check_result"] = fact_check
            state["current_agent"] = "citation"
            return state
            
        except Exception as e:
            error_msg = f"Error in fact checking: {str(e)}"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            return state

class DataAnalysisNode:
    """Node for analyzing numerical data in research results."""
    def __init__(self, data_analysis_agent: DataAnalysisAgent):
        self.data_analysis_agent = data_analysis_agent

    async def __call__(self, state: AgentState) -> Union[AgentState, str]:
        """Execute data analysis step."""
        try:
            logger.info("Starting data analysis of research results")
            analysis = await self.data_analysis_agent.process_message({
                "research_results": state["research_results"],
                "query": state["query"]
            })
            
            state["data_analysis_result"] = analysis
            state["current_agent"] = "citation"
            return state
            
        except Exception as e:
            error_msg = f"Error in data analysis: {str(e)}"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            return state

class CodeAnalysisNode:
    """Node for analyzing code snippets in research results."""
    def __init__(self, code_analysis_agent: CodeAnalysisAgent):
        self.code_analysis_agent = code_analysis_agent

    async def __call__(self, state: AgentState) -> Union[AgentState, str]:
        """Execute code analysis step."""
        try:
            logger.info("Starting code analysis of research results")
            analysis = await self.code_analysis_agent.process_message({
                "research_results": state["research_results"],
                "query": state["query"]
            })
            
            state["code_analysis_result"] = analysis
            state["current_agent"] = "citation"
            return state
            
        except Exception as e:
            error_msg = f"Error in code analysis: {str(e)}"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            return state

class CitationNode:
    """Node for managing citations and sources."""
    def __init__(self, citation_agent: CitationAgent):
        self.citation_agent = citation_agent

    async def __call__(self, state: AgentState) -> Union[AgentState, str]:
        """Execute citation management step."""
        try:
            logger.info("Starting citation processing of research results")
            citations = await self.citation_agent.process_message({
                "research_results": state["research_results"],
                "query": state["query"]
            })
            
            state["citations"] = citations
            state["current_agent"] = "synthesis"
            return state
            
        except Exception as e:
            error_msg = f"Error in citation processing: {str(e)}"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            return state

class SynthesisNode:
    """Node for synthesizing research results."""
    def __init__(self, synthesis_agent: SynthesisAgent):
        self.synthesis_agent = synthesis_agent

    async def __call__(self, state: AgentState) -> Union[AgentState, str]:
        """Execute synthesis step."""
        try:
            logger.info("Starting synthesis of research results")
            message = {
                "research_results": state["research_results"],
                "fact_check_result": state.get("fact_check_result"),
                "data_analysis_result": state.get("data_analysis_result"),
                "code_analysis_result": state.get("code_analysis_result"),
                "citations": state.get("citations"),
                "query": state["query"]
            }
            synthesis = await self.synthesis_agent.process_message(message)
            
            state["synthesis_result"] = synthesis.get("synthesis", {})
            state["current_agent"] = "end"
            return state
            
        except Exception as e:
            error_msg = f"Error in synthesis step: {str(e)}"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            return state

class Orchestrator:
    def __init__(self):
        """Initialize the orchestrator with LangGraph workflow."""
        # Initialize all agents
        self.query_refinement_agent = QueryRefinementAgent()
        self.research_agent = ResearchAgent()
        self.fact_checking_agent = FactCheckingAgent()
        self.data_analysis_agent = DataAnalysisAgent()
        self.code_analysis_agent = CodeAnalysisAgent()
        self.citation_agent = CitationAgent()
        self.synthesis_agent = SynthesisAgent()
        
        # Create workflow nodes
        self.query_node = QueryRefinementNode(query_agent=self.query_refinement_agent)
        self.research_node = ResearchNode(research_agent=self.research_agent)
        self.fact_check_node = FactCheckNode(fact_checking_agent=self.fact_checking_agent)
        self.data_analysis_node = DataAnalysisNode(data_analysis_agent=self.data_analysis_agent)
        self.code_analysis_node = CodeAnalysisNode(code_analysis_agent=self.code_analysis_agent)
        self.citation_node = CitationNode(citation_agent=self.citation_agent)
        self.synthesis_node = SynthesisNode(synthesis_agent=self.synthesis_agent)
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add all nodes
        workflow.add_node("query_refinement", self.query_node)
        workflow.add_node("research", self.research_node)
        workflow.add_node("fact_check", self.fact_check_node)
        workflow.add_node("data_analysis", self.data_analysis_node)
        workflow.add_node("code_analysis", self.code_analysis_node)
        workflow.add_node("citation", self.citation_node)
        workflow.add_node("synthesis", self.synthesis_node)
        
        # Define routing logic
        def route_next(state: AgentState) -> str:
            if bool(state.get("errors")):
                return END
            
            current = state["current_agent"]
            routes = {
                "query_refinement": "research",
                "research": "fact_check",
                "fact_check": "data_analysis",
                "data_analysis": "code_analysis",
                "code_analysis": "citation",
                "citation": "synthesis",
                "synthesis": END
            }
            
            next_node = routes.get(current, END)
            if next_node != END:
                state["current_agent"] = next_node
            return next_node
            
        # Add edges between nodes
        workflow.add_edge("query_refinement", "research")
        workflow.add_edge("research", "fact_check")
        workflow.add_edge("fact_check", "data_analysis")
        workflow.add_edge("data_analysis", "code_analysis")
        workflow.add_edge("code_analysis", "citation")
        workflow.add_edge("citation", "synthesis")
        workflow.add_edge("synthesis", END)
        
        workflow.set_entry_point("query_refinement")
        
        # Compile the graph
        self.graph = workflow.compile()
    
    async def execute(self, query: str) -> Dict:
        """Execute the research workflow using LangGraph.
        
        Args:
            query (str): Research query
            
        Returns:
            Dict: Final workflow results
        """
        try:
            # Initialize state
            state = AgentState(
                query=query,
                refined_query=None,
                sub_queries=[],
                research_results=[],
                synthesis_result=None,
                fact_check_result=None,
                data_analysis_result=None,
                citations=None,
                code_analysis_result=None,
                errors=[],
                current_agent="query_refinement"
            )
            
            # Execute the graph
            final_state = await self.graph.ainvoke(state)
            
            return {
                'status': 'completed' if not final_state["errors"] else 'error',
                'research_results': final_state["research_results"],
                'synthesis_result': final_state["synthesis_result"],
                'errors': final_state["errors"]
            }
            
        except Exception as e:
            error_msg = f"Error in research workflow: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'research_results': [],
                'synthesis_result': None,
                'errors': [error_msg]
            }
