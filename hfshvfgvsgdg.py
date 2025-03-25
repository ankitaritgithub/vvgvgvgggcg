import os
import base64
import subprocess
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict
from fastapi import FastAPI, HTTPException, Request
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

class AgentStateDict(TypedDict):
    prompt: str
    available_files: Optional[List[str]]
    selected_files: Optional[List[str]]
    test_results: Optional[str]
    analysis: Optional[Dict[str, Any]]
    test_content: Optional[str]
    messages: List[Dict[str, str]]
    error_message: Optional[str]

class FileContent(BaseModel):
    file_extension: str  # File type, e.g., ".js", ".txt"
    content: str  # Base64 encoded string: "<base64_filename>|<base64_file_content>"

class UploadFileRequest(BaseModel):
    prompt: str
    file_content: List[FileContent]

class TestRequest(BaseModel):
    prompt: str
    file_content: Optional[List[FileContent]] = None

class TestAnalysisResponse(BaseModel):
    """Structured response for test analysis"""
    task_type: str = Field(
        description="Type of task: 'generate_data' or 'run_tests'"
    )
    selected_files: List[str] = Field(
        default_factory=list,
        description="List of selected test files"
    )
    data_generation_required: bool = Field(
        description="Whether data generation is needed"
    )
    csv_content: Optional[str] = Field(
        default=None,
        description="CSV content if data generation is required"
    )
    command_type: Optional[str] = Field(
        default=None,
        description="Type of test command to run (e.g., 'test all', 'debug', etc.)"
    )

def upload_files_to_tests_folder(files: List[FileContent]) -> List[str]:
    """
    Upload files to the tests folder
    
    Args:
        files: List of FileContent objects with file_extension (file type) and content (base64 encoded "<filename>|<content>")
        
    Returns:
        List of saved file paths
    """
    saved_files = []
    tests_folder = './tests'
    
    # Create tests folder if it doesn't exist
    if not os.path.exists(tests_folder):
        os.makedirs(tests_folder)
    
    for file in files:
        # Initialize decoded_filename to avoid referencing it before assignment
        decoded_filename = None
        
        try:
            # Split content into base64_filename and base64_file_content
            base64_filename, base64_file_content = file.content.split('|')
            
            # Decode base64 filename
            decoded_filename = base64.b64decode(base64_filename).decode('utf-8')
            
            # Add file extension to the decoded filename
            decoded_filename_with_extension = f"{decoded_filename}{file.file_extension}"
            
            # Decode base64 file content
            decoded_content = base64.b64decode(base64_file_content)
            
            # Generate file path using the decoded filename with extension
            file_path = os.path.join(tests_folder, decoded_filename_with_extension)
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(decoded_content)
            
            saved_files.append(decoded_filename_with_extension)
            
        except Exception as e:
            # Use the decoded_filename if it was assigned, otherwise use a placeholder
            filename_for_error = decoded_filename if decoded_filename else "unknown_file"
            raise Exception(f"Error saving file {filename_for_error}: {str(e)}")
    
    return saved_files

def list_files_in_tests_folder(state: Dict[str, Any]) -> Dict[str, Any]:
    """Lists all test files in the tests folder and updates the state."""
    try:
        directory = './tests'
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        state["available_files"] = files if files else []
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append({
            "role": "system",
            "content": f"Available test files: {', '.join(files)}"
        })
    except Exception as e:
        state["error_message"] = f"Error listing test files: {str(e)}"
    return state

def analyze_user_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes user prompt with structured output"""
    try:
        if not state.get("prompt"):
            state["error_message"] = "No user prompt provided"
            return state

        prompt_template = f"""
        Analyze the following request and provide a structured response:
        
        Available test files: {state.get('available_files', [])}
        User request: {state.get('prompt')}

        Determine if this is a data generation request or a test execution request.
        For data generation, provide CSV content.
        For test execution, based on user_prompt selected files, execute the command as per the user prompt request.
        
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
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        # Get structured response
        structured_model = model.with_structured_output(TestAnalysisResponse)
        response = structured_model.invoke(prompt_template)
        
        # Update state based on structured response
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
        
    except Exception as e:
        state["error_message"] = f"Error analyzing prompt: {str(e)}"
    return state

def create_and_save_file(state: Dict[str, Any]) -> Dict[str, Any]:
    """Create and save CSV file if data generation is required"""
    analysis = state.get("analysis", {})
    if not isinstance(analysis, dict):
        analysis = analysis.dict()
    
    if analysis.get("data_generation_required"):
        try:
            folder_name = "testdata"
            file_path = os.path.join(folder_name, "testdata.csv")
            
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)
            
            with open(file_path, 'w') as file:
                file.write(state.get("test_content", ""))
            
            state["messages"].append({
                "role": "system",
                "content": f"Generated data saved to {file_path}"
            })
        except Exception as e:
            state["error_message"] = f"File handling error: {e}"
    
    return state

def run_playwright_tests(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Playwright tests based on structured analysis"""
    analysis = state.get("analysis", {})
    if not isinstance(analysis, dict):
        analysis = analysis.dict()
    
    if analysis.get("task_type") == "run_tests":
        try:
            # Get selected files first
            selected_files = state.get("selected_files", [])
            if not selected_files:
                state["error_message"] = "No test files selected for execution"
                return state
            
            # Get the first test file for single-file commands
            test_file = f"tests/{selected_files[0]}"

            # Get the user prompt from state
            user_prompt = state.get("prompt", "").lower()

            # Initialize command as None
            command = None

            # Define command patterns dictionary
            command_patterns = {
                "test all": f"npx playwright test {test_file}",
                "report": f"npx playwright show-report",
                "debug": f"npx playwright test {test_file} --debug",
                "ui mode": f"npx playwright test --ui",
                "headed": f"npx playwright test {test_file} --headed",
                "webkit": f"npx playwright test --project=webkit",
                "firefox": f"npx playwright test --project=firefox",
                "chrome": f"npx playwright test --project=chromium"
            }
            
            for keyword, cmd in command_patterns.items():
                if keyword in user_prompt:
                    command = cmd
                    break
            
            if not command:
                command = command_patterns["test all"]
            
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
            
            # Update state with results
            state["test_results"] = test_result.stdout
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append({
                "role": "system",
                "content": f"Test execution completed successfully using command: {command}"
            })
            
        except subprocess.CalledProcessError as e:
            state["error_message"] = f"Test execution failed: {e.stderr}"
        except subprocess.TimeoutExpired as e:
            state["error_message"] = f"Test execution timed out after 300 seconds"
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

from pydantic import parse_obj_as

@app.post("/run_tests")
async def run_tests(request: Request):
    """API endpoint to handle test execution requests and file uploads."""
    try:
        # Log the incoming request
        payload = await request.json()  # Await the JSON payload
        logger.debug(f"Incoming request: {payload}")

        # Parse the request payload
        prompt = payload.get("prompt")
        file_content = payload.get("file_content")

        # Initialize state
        initial_state = {
            "prompt": prompt,
            "available_files": None,
            "selected_files": None,
            "test_results": None,
            "analysis": None,
            "messages": [],
            "error_message": None
        }

        # Handle file uploads if present
        if file_content:
            try:
                # Parse file_content into a list of FileContent objects
                file_content_objects = parse_obj_as(List[FileContent], file_content)
                uploaded_files = upload_files_to_tests_folder(file_content_objects)
                # Add upload info to messages
                initial_state["messages"].append({
                    "role": "system",
                    "content": f"Uploaded {len(file_content_objects)} file(s) to tests folder"
                })
            except Exception as e:
                logger.error(f"File upload failed: {str(e)}")
                raise HTTPException(status_code=400, detail=f"File upload failed: {str(e)}")

        # Create workflow
        workflow = create_workflow_graph()

        # Run workflow
        final_state = workflow.invoke(initial_state)

        # Log the final state
        logger.debug(f"Final state: {final_state}")

        return {
            "status": "success" if not final_state.get("error_message") else "error",
            "available_files": final_state.get("available_files"),
            "selected_files": final_state.get("selected_files"),
            "analysis": final_state.get("analysis"),
            "test_results": final_state.get("test_results"),
            "messages": final_state.get("messages"),
            "error": final_state.get("error_message")
        }
    except Exception as e:
        logger.error(f"Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
