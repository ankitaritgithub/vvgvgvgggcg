import os
import base64
import subprocess
import zipfile
import uuid
from datetime import datetime
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
    extracted_repo_path: Optional[str]  # New field to store extracted repo path

class FileContent(BaseModel):
    file_extension: str  # File type, e.g., ".js", ".txt", ".zip"
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


def upload_files_to_tests_folder(files: List[FileContent]) -> Dict[str, Any]:
    """
    Upload files to the tests folder, handling ZIP and JS files differently
    
    ZIP files: content only (base64 encoded zip data) - extracts directly to playwrightscript
    JS files: filename|content format (base64_filename|base64_content)
    """
    result = {
        "saved_files": [],
        "extracted_repo_path": None
    }
    
    tests_folder = './tests'
    gui_testing_folder = './gui_testing_agent'
    
    # Create folders if they don't exist
    for folder in [tests_folder, gui_testing_folder]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    for file in files:
        try:
            # Ensure file extension starts with dot
            if not file.file_extension.startswith('.'):
                file.file_extension = f".{file.file_extension.lower()}"
            
            # Handle ZIP files (content only)
            if file.file_extension == '.zip':
                # Final extraction folder name
                final_folder_name = "playwrightscript"
                final_extracted_path = os.path.join(gui_testing_folder, final_folder_name)
                
                # Use original filename for the ZIP file
                if '|' in file.content:
                    base64_filename, base64_file_content = file.content.split('|', 1)
                    zip_name = base64.b64decode(base64_filename).decode('utf-8') + '.zip'
                else:
                    zip_name = "uploaded_file.zip"
                
                zip_path = os.path.join(gui_testing_folder, zip_name)
                
                # Decode and save the ZIP file
                decoded_content = base64.b64decode(file.content.split('|')[-1])
                with open(zip_path, 'wb') as f:
                    f.write(decoded_content)
                
                # Remove existing folder if it exists
                if os.path.exists(final_extracted_path):
                    import shutil
                    shutil.rmtree(final_extracted_path)
                
                # Create the final directory
                os.makedirs(final_extracted_path)
                
                # Extract directly to final folder
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Get the root folder in the zip (if any)
                    root_folder = None
                    for name in zip_ref.namelist():
                        if name.endswith('/'):
                            root_folder = name
                            break
                    
                    # Extract all files, skipping the root folder if it exists
                    for member in zip_ref.infolist():
                        member_path = member.filename
                        if root_folder and member_path.startswith(root_folder):
                            member_path = member_path[len(root_folder):]
                        
                        # Skip directories
                        if not member_path:
                            continue
                        
                        # Extract to final path
                        target_path = os.path.join(final_extracted_path, member_path)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        if not member.is_dir():
                            with open(target_path, 'wb') as outfile:
                                outfile.write(zip_ref.read(member))
                
                result["extracted_repo_path"] = final_extracted_path
                logger.info(f"Extracted ZIP directly to: {final_extracted_path}")
                
                # Add the extracted files to saved_files
                for root, _, files_in_zip in os.walk(final_extracted_path):
                    for file_in_zip in files_in_zip:
                        result["saved_files"].append(os.path.join(root, file_in_zip))
            
            # Handle JS files (filename|content)
            elif file.file_extension == '.js':
                if '|' not in file.content:
                    raise ValueError("JS files must be in 'filename|content' format")
                
                base64_filename, base64_file_content = file.content.split('|', 1)
                
                # Decode filename and content
                decoded_filename = base64.b64decode(base64_filename).decode('utf-8')
                decoded_filename_with_extension = f"{decoded_filename}{file.file_extension}"
                decoded_content = base64.b64decode(base64_file_content)
                
                # Save to tests folder
                file_path = os.path.join(tests_folder, decoded_filename_with_extension)
                with open(file_path, 'wb') as f:
                    f.write(decoded_content)
                result["saved_files"].append(decoded_filename_with_extension)
            
            else:
                raise ValueError(f"Unsupported file type: {file.file_extension}")
            
        except Exception as e:
            filename_for_error = decoded_filename if 'decoded_filename' in locals() else "unknown_file"
            raise Exception(f"Error saving file {filename_for_error}: {str(e)}")
    
    return result

def list_files_in_tests_folder(state: Dict[str, Any]) -> Dict[str, Any]:
    """Lists all test files in the tests folder and updates the state."""
    try:
        directory = '../GUIagentTask/gui_testing_agent/playwrightscript/tests'
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
            api_key="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"
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
    """Execute Playwright tests after navigating to the extracted directory"""
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
            
            # Define the target directory path
            target_dir = os.path.expanduser(
                "~/Desktop/zipfile/GUIagentTask/gui_testing_agent/playwrightscript/"
            )
            
            # Verify the target directory exists
            if not os.path.exists(target_dir):
                raise Exception(f"Target directory does not exist: {target_dir}")
            
            # Store the original working directory
            original_dir = os.getcwd()
            
            try:
                # Change to the target directory
                os.chdir(target_dir)
                print(f"Changed working directory to: {os.getcwd()}")

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
                
                # Determine the base command based on user prompt
                for keyword, cmd in command_patterns.items():
                    if keyword in user_prompt:
                        command = cmd
                        break
                
                if not command:
                    command = command_patterns["test all"]
            
                print(f"Executing Playwright command: {command}")
                
                print(f"Executing Playwright command: {command}")
                print(f"Current directory: {os.getcwd()}")
                
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
                
            finally:
                # Always return to the original directory
                os.chdir(original_dir)
                print(f"Restored working directory to: {original_dir}")
            
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
            "error_message": None,
            "extracted_repo_path": None  # Initialize new field
        }

        # Handle file uploads if present
        if file_content:
            try:
                # Parse file_content into a list of FileContent objects
                file_content_objects = parse_obj_as(List[FileContent], file_content)
                upload_result = upload_files_to_tests_folder(file_content_objects)
                
                # Update state with upload results
                initial_state["available_files"] = upload_result["saved_files"]
                initial_state["extracted_repo_path"] = upload_result["extracted_repo_path"]
                
                # Add upload info to messages
                initial_state["messages"].append({
                    "role": "system",
                    "content": f"Uploaded {len(file_content_objects)} file(s)"
                })
                
                if upload_result["extracted_repo_path"]:
                    initial_state["messages"].append({
                        "role": "system",
                        "content": f"Extracted ZIP to: {upload_result['extracted_repo_path']}"
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
            "error": final_state.get("error_message"),
            "extracted_repo_path": final_state.get("extracted_repo_path")  # Include in response
        }
    except Exception as e:
        logger.error(f"Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)