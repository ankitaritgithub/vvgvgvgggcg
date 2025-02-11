import os
import json
import subprocess
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict
from fastapi import FastAPI, HTTPException

app = FastAPI()

class Checkpoint(BaseModel):
    """Model for storing conversation checkpoints"""
    conversation_id: str
    timestamp: str
    state: Dict[str, Any]
    messages: List[Dict[str, str]]

class AgentStateDict(TypedDict):
    conversation_id: str
    prompt: str
    available_files: Optional[List[str]]
    selected_files: Optional[List[str]]
    test_results: Optional[str]
    analysis: Optional[Dict[str, Any]]
    test_content: Optional[str]
    messages: List[Dict[str, str]]
    error_message: Optional[str]

class TestRequest(BaseModel):
    prompt: str
    conversation_id: Optional[str] = None

class TestAnalysisResponse(BaseModel):
    """Structured response for test analysis"""
    task_type: str = Field(description="Type of task: 'generate_data' or 'run_tests'")
    selected_files: List[str] = Field(default_factory=list, description="List of selected test files")
    data_generation_required: bool = Field(description="Whether data generation is needed")
    csv_content: Optional[str] = Field(default=None, description="CSV content if data generation is required")
    command_type: Optional[str] = Field(default=None, description="Type of test command to run")

class CheckpointManager:
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)

    def save_checkpoint(self, conversation_id: str, state: Dict[str, Any]) -> None:
        """Save current state as a checkpoint"""
        checkpoint = Checkpoint(
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat(),
            state=state,
            messages=state.get("messages", [])
        )
        
        file_path = os.path.join(self.checkpoint_dir, f"{conversation_id}.json")
        with open(file_path, "w") as f:
            json.dump(checkpoint.dict(), f, indent=2)

    def load_checkpoint(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Load state from a checkpoint"""
        file_path = os.path.join(self.checkpoint_dir, f"{conversation_id}.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                checkpoint_data = json.load(f)
                return checkpoint_data["state"]
        return None

    def generate_conversation_id(self) -> str:
        """Generate a unique conversation ID"""
        return datetime.now().strftime("%Y%m%d-%H%M%S-") + os.urandom(4).hex()

checkpoint_manager = CheckpointManager()

def list_files_in_tests_folder(state: Dict[str, Any]) -> Dict[str, Any]:
    """Lists all test files in the tests folder and updates the state."""
    try:
        directory = './tests'
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        state["available_files"] = files if files else []
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append({
            "role": "system",
            "content": f"Available test files: {', '.join(files)}"
        })
        
        # Save checkpoint after updating state
        if "conversation_id" in state:
            checkpoint_manager.save_checkpoint(state["conversation_id"], state)
    except Exception as e:
        state["error_message"] = f"Error listing test files: {str(e)}"
    return state

def analyze_user_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes user prompt with structured output"""
    try:
        if not state.get("prompt"):
            state["error_message"] = "No user prompt provided"
            return state

        # Load previous context from messages if available
        previous_context = ""
        if state.get("messages"):
            previous_context = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in state["messages"][-3:]  # Get last 3 messages for context
            ])

        prompt_template = f"""
        Previous context:
        {previous_context}

        Analyze the following request and provide a structured response:
        
        Available test files: {state.get('available_files', [])}
        User request: {state.get('prompt')}

        Determine if this is a data generation request or a test execution request.
        For data generation, provide CSV content.
        For test execution, select relevant test files and command type.
        
        Respond in the following JSON format:
        {{
            "task_type": "generate_data" or "run_tests",
            "selected_files": [],
            "data_generation_required": true/false,
            "csv_content": "optional csv content",
            "command_type": "optional command type"
        }}
        """

        model = ChatGroq(
            temperature=0,
            model_name="llama-3.3-70b-versatile",
            api_key="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"
        )
        
        structured_model = model.with_structured_output(TestAnalysisResponse)
        response = structured_model.invoke(prompt_template)
        
        state["analysis"] = response.dict()
        state["selected_files"] = response.selected_files
        
        if response.data_generation_required:
            state["test_content"] = response.csv_content
        else:
            state["command_type"] = response.command_type
            
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append({
            "role": "assistant",
            "content": f"Analysis complete. Task type: {response.task_type}"
        })
        
        # Save checkpoint after analysis
        if "conversation_id" in state:
            checkpoint_manager.save_checkpoint(state["conversation_id"], state)
        
    except Exception as e:
        state["error_message"] = f"Error analyzing prompt: {str(e)}"
    return state

def create_and_save_file(state: Dict[str, Any]) -> Dict[str, Any]:
    """Create and save CSV file if data generation is required"""
    try:
        analysis = state.get("analysis", {})
        if not isinstance(analysis, dict):
            analysis = analysis.dict()
        
        if analysis.get("data_generation_required"):
            folder_name = "testdata"
            file_path = os.path.join(folder_name, "testdata.csv")
            
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)
            
            with open(file_path, 'w') as file:
                file.write(state.get("test_content", ""))
            
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append({
                "role": "system",
                "content": f"Generated data saved to {file_path}"
            })
            
            # Save checkpoint after file creation
            if "conversation_id" in state:
                checkpoint_manager.save_checkpoint(state["conversation_id"], state)
                
    except Exception as e:
        state["error_message"] = f"File handling error: {e}"
    
    return state

def run_playwright_tests(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Playwright tests based on structured analysis"""
    try:
        analysis = state.get("analysis", {})
        if not isinstance(analysis, dict):
            analysis = analysis.dict()
        
        if analysis.get("task_type") == "run_tests":
            selected_files = state.get("selected_files", [])
            if not selected_files:
                state["error_message"] = "No test files selected for execution"
                return state
            
            test_file = f"tests/{selected_files[0]}"
            user_prompt = state.get("prompt", "").lower()

            command_patterns = {
                "test": f"npx playwright test {test_file}",
                "report in html": f"npx playwright show-report",
                "debug": f"npx playwright test {test_file} --debug",
                "ui mode": f"npx playwright test --ui",
                "headed": f"npx playwright test {test_file} --headed",
                "webkit": f"npx playwright test --project=webkit",
                "firefox": f"npx playwright test --project=firefox",
                "chrome": f"npx playwright test --project=chromium",
                "json format": f"PLAYWRIGHT_JSON_OUTPUT_NAME=results.json npx playwright test --reporter=json",
                "test all": f"npx playwright test"
            }
            
            command = None
            for keyword, cmd in command_patterns.items():
                if keyword in user_prompt:
                    command = cmd
                    break
            
            if not command:
                try:
                    model = ChatGroq(
                        temperature=0,
                        model_name="llama-3.3-70b-versatile",
                        api_key="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"
                    )
                    
                    response = model.invoke(
                        f"The test case for query '{user_prompt}' does not exist. Please provide guidance on what kind of test should be created for this scenario."
                    )
                    
                    if "messages" not in state:
                        state["messages"] = []
                    state["messages"].append({
                        "role": "system",
                        "content": f"Test case not found. Model suggestion:\n{response.content}"
                    })
                    
                    state["test_results"] = "No test executed - awaiting test case creation based on model suggestion"
                    
                    # Save checkpoint after getting model suggestion
                    if "conversation_id" in state:
                        checkpoint_manager.save_checkpoint(state["conversation_id"], state)
                        
                    return state
                
                except Exception as e:
                    state["error_message"] = f"Error getting model suggestion: {str(e)}"
                    state["messages"].append({
                        "role": "system",
                        "content": "Please try a different test case or check the available test cases."
                    })
                    return state
            
            print(f"Executing Playwright command: {command}")
            
            # Execute command
            test_result = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300
            )
            
            print("Playwright Tests completed successfully!")
            print("Output:\n", test_result.stdout)
            
            state["test_results"] = test_result.stdout
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append({
                "role": "system",
                "content": f"Test execution completed successfully using command: {command}"
            })
            
            # Save checkpoint after test execution
            if "conversation_id" in state:
                checkpoint_manager.save_checkpoint(state["conversation_id"], state)
            
    except subprocess.CalledProcessError as e:
        state["error_message"] = f"Test execution failed: {e.stderr}"
    except subprocess.TimeoutExpired:
        state["error_message"] = "Test execution timed out after 300 seconds"
    except Exception as e:
        state["error_message"] = f"Test execution error: {str(e)}"
    
    return state

def create_workflow_graph():
    """Creates the workflow graph with the execution flow."""
    graph = StateGraph(AgentStateDict)
    
    # Add nodes
    graph.add_node("list_files", list_files_in_tests_folder)
    graph.add_node("analyze_prompt", analyze_user_prompt)
    graph.add_node("create_and_save_file", create_and_save_file)
    graph.add_node("run_tests", run_playwright_tests)
    
    # Define the flow
    graph.add_edge(START, "list_files")
    graph.add_edge("list_files", "analyze_prompt")
    graph.add_edge("analyze_prompt", "create_and_save_file")
    graph.add_edge("create_and_save_file", "run_tests")
    graph.add_edge("run_tests", END)
    
    return graph.compile()

@app.post("/run_tests")
async def run_tests(request: TestRequest):
    """API endpoint to handle test execution requests."""
    try:
        workflow = create_workflow_graph()
        
        # Handle conversation continuity
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = checkpoint_manager.generate_conversation_id()
        
        # Try to load existing state from checkpoint
        initial_state = checkpoint_manager.load_checkpoint(conversation_id)
        
        if initial_state is None:
            # Create new state if no checkpoint exists
            initial_state = {
                "conversation_id": conversation_id,
                "prompt": request.prompt,
                "available_files": None,
                "selected_files": None,
                "test_results": None,
                "analysis": None,
                "messages": [],
                "error_message": None
            }
        else:
            # Update existing state with new prompt
            initial_state["prompt"] = request.prompt
        
        final_state = workflow.invoke(initial_state)
        
        # Save final state
        checkpoint_manager.save_checkpoint(conversation_id, final_state)
        
        return {
            "status": "success" if not final_state.get("error_message") else "error",
            "conversation_id": conversation_id,
            "available_files": final_state.get("available_files"),
            "selected_files": final_state.get("selected_files"),
            "analysis": final_state.get("analysis"),
            "test_results": final_state.get("test_results"),
            "messages": final_state.get("messages"),
            "error": final_state.get("error_message")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
