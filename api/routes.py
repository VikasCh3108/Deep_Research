"""
API Routes: FastAPI routes for the research system.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Optional
from core.orchestrator import Orchestrator
import uuid
import logging

# Configure logger for API routes
logger = logging.getLogger('api')

app = FastAPI(title="Deep Research AI System")

# Setup static and template directories
static_dir = Path(__file__).parent.parent / "static"
templates_dir = Path(__file__).parent.parent / "templates"

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Create static directory if it doesn't exist
static_dir.mkdir(exist_ok=True)
for subdir in ['css', 'js']:
    (static_dir / subdir).mkdir(exist_ok=True)

# Store for tracking research tasks
research_tasks: Dict[str, Dict] = {}

class ResearchRequest(BaseModel):
    """Research request model"""
    query: str
    
class TaskResponse(BaseModel):
    """Task response model"""
    task_id: str
    status: str

# Initialize orchestrator
orchestrator = Orchestrator()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main page"""
    index_path = templates_dir / "index.html"
    return HTMLResponse(content=index_path.read_text(), media_type="text/html")

async def process_research(task_id: str, query: str):
    """
    Process research query in background.
    
    Args:
        task_id (str): Unique task identifier
        query (str): Research query
    """
    try:
        logger.info(f"Processing research task {task_id} for query: {query}")
        result = await orchestrator.execute(query)
        
        if result.get("status") == "error":
            research_tasks[task_id].update({
                "status": "failed",
                "error": result.get("errors", ["Unknown error"])[0],
                "result": result
            })
            logger.error(f"Research task {task_id} failed: {result.get('errors')}")
        else:
            research_tasks[task_id].update({
                "status": "completed",
                "result": result
            })
            logger.info(f"Research task {task_id} completed successfully")
            
    except Exception as e:
        error_msg = f"Error processing research: {str(e)}"
        logger.error(error_msg)
        research_tasks[task_id].update({
            "status": "failed",
            "error": error_msg
        })

@app.post("/research", response_model=TaskResponse)
async def create_research_task(request: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Create a new research task.
    
    Args:
        request (ResearchRequest): Research request
        background_tasks (BackgroundTasks): Background tasks handler
        
    Returns:
        TaskResponse: Task information
    """
    task_id = str(uuid.uuid4())
    logger.info(f"Creating new research task {task_id} for query: {request.query}")
    
    research_tasks[task_id] = {"status": "processing"}
    logger.debug(f"Initialized task state for {task_id}")
    
    logger.info(f"Adding research task {task_id} to background tasks")
    background_tasks.add_task(process_research, task_id, request.query)
    
    logger.debug(f"Research task {task_id} created successfully")
    return TaskResponse(task_id=task_id, status="processing")

@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get status of a research task.
    
    Args:
        task_id (str): Task identifier
        
    Returns:
        Dict: Task status information
    """
    logger.debug(f"Checking status for task {task_id}")
    
    if task_id not in research_tasks:
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = research_tasks[task_id]
    logger.debug(f"Retrieved task {task_id} with status: {task['status']}")
    
    # Format the response to be more concise
    if task["status"] == "completed":
        result = task["result"]
        synthesis = result.get("synthesis_result", {})
        response = {
            "status": "completed",
            "result": {
                "summary": synthesis.get("summary", ""),
                "key_points": synthesis.get("key_points", []),
                "sources": synthesis.get("sources", []),
                "confidence_score": synthesis.get("confidence_score", 0.0)
            }
        }
        logger.info(f"Task {task_id} completed with confidence score: {synthesis.get('confidence_score', 0.0)}")
        return response
    elif task["status"] == "failed":
        error = task.get("error", "Unknown error")
        logger.error(f"Task {task_id} failed with error: {error}")
        return {
            "status": "failed",
            "error": error
        }
    else:
        logger.debug(f"Task {task_id} is still processing")
        return {"status": task["status"]}

@app.get("/results/{task_id}")
async def get_task_results(task_id: str):
    """
    Get results of a completed research task.
    
    Args:
        task_id (str): Task identifier
        
    Returns:
        Dict: Task results
    """
    logger.debug(f"Retrieving results for task {task_id}")
    
    if task_id not in research_tasks:
        logger.warning(f"Task {task_id} not found when retrieving results")
        raise HTTPException(status_code=404, detail="Task not found")
        
    task = research_tasks[task_id]
    logger.debug(f"Retrieved task {task_id} with status: {task['status']}")
    
    if task["status"] != "completed":
        logger.warning(f"Attempted to get results for incomplete task {task_id}")
        raise HTTPException(status_code=400, detail="Task not completed")
    
    logger.info(f"Returning results for completed task {task_id}")
    return task["result"]
