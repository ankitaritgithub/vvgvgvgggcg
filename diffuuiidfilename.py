import os
import base64
import subprocess
from uuid import UUID
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
import logging
import json
import zipfile
import uuid  # Add this import at the top with other imports

# ========== SETUP & CONFIGURATION ==========
# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="GUI Testing Automation API",
    description="API for executing Playwright tests with AI analysis",
    version="1.0.0"
)

# ========== DATA MODELS ==========
class AgentStateDict(TypedDict):
    """State dictionary for the workflow graph nodes"""
    prompt: str                      # User's original request
    available_files: Optional[List[str]]  # List of available test files
    selected_files: Optional[List[str]]   # Files selected for execution
    test_results: Optional[str]       # Raw test execution output
    analysis: Optional[Dict[str, Any]] # AI analysis of the request
    test_content: Optional[str]       # Generated test data content
    messages: List[Dict[str, str]]    # System messages during execution
    error_message: Optional[str]      # Any error that occurred
    execution_command: Optional[str]  # Final command used to run tests

class FileContent(BaseModel):
    """Model for file upload content"""
    file_extension: str = Field(..., description="File type extension (e.g., '.js', '.txt')")
    content: str = Field(..., description="Base64 encoded string: '<base64_filename>|<base64_file_content>'")

class ChatMessage(BaseModel):
    """Model for chat history messages"""
    content: str = Field(..., description="Message content")
    role: str = Field(..., description="'user' or 'assistant'")
    name: str = Field(default="GuiTestingAgent", description="Agent name")

class ChatResponse(BaseModel):
    """Response model for API endpoints"""
    chat_id: str = Field(..., description="Unique chat session identifier")
    chat_history: List[ChatMessage] = Field(..., description="Conversation history")
    download_url: Optional[str] = Field(default=None, description="URL for test report download")

class ChatRequest(BaseModel):
    """Request model for API endpoints"""
    id: str = Field(..., description="Unique chat session identifier")
    prompt: str = Field(..., description="User's test execution request")
    file_content: Optional[List[FileContent]] = Field(default=None, description="Files to upload")

# ========== CORE FUNCTIONS ==========
def upload_files_to_tests_folder(files: List[FileContent]) -> List[str]:
    """
    Uploads files to the tests folder with special handling for ZIP files and spec.js files
    Returns list of saved filenames
    """
    saved_files = []
    base_tests_folder = '../Extractplaywrightfile/'
    os.makedirs(base_tests_folder, exist_ok=True)
    
    for file in files:
        try:
            # Handle the file content (which might be just content or filename|content)
            parts = file.content.split('|')
            
            if len(parts) == 2:
                # Format: <base64_filename>|<base64_file_content>
                base64_filename, base64_content = parts
                try:
                    decoded_filename = base64.b64decode(base64_filename).decode('utf-8')
                    decoded_content = base64.b64decode(base64_content)
                except (base64.binascii.Error, UnicodeDecodeError) as e:
                    raise Exception(f"Invalid base64 encoding: {str(e)}")
            else:
                # Format: <base64_file_content> (no filename provided)
                base64_content = file.content
                try:
                    decoded_content = base64.b64decode(base64_content)
                except base64.binascii.Error as e:
                    raise Exception(f"Invalid base64 content: {str(e)}")
                decoded_filename = f"uploaded_file_{uuid.uuid4().hex[:8]}"
            
            # Handle ZIP file upload
            if file.file_extension.lower() == '.zip':
                # Create unique folder name for the extracted content
                unique_folder = f"playwright_tests_{uuid.uuid4().hex[:8]}"
                extraction_path = os.path.join(base_tests_folder, unique_folder)
                os.makedirs(extraction_path, exist_ok=True)
                
                # Save the zip file temporarily
                zip_filename = f"{unique_folder}.zip"
                zip_path = os.path.join(extraction_path, zip_filename)
                with open(zip_path, 'wb') as f:
                    f.write(decoded_content)
                
                # Extract the zip file
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extraction_path)
                    
                    # Remove the temporary zip file
                    os.remove(zip_path)
                    
                    # Find all spec.js files in the extracted directory
                    for root, _, files_in_zip in os.walk(extraction_path):
                        for f in files_in_zip:
                            if f.endswith('.spec.js'):
                                relative_path = os.path.relpath(os.path.join(root, f), base_tests_folder)
                                saved_files.append(relative_path)
                    
                    logger.info(f"Extracted ZIP file to {extraction_path}")
                    saved_files.append(f"ZIP_EXTRACTED:{unique_folder}")
                except zipfile.BadZipFile:
                    logger.error(f"Invalid ZIP file: {zip_path}")
                    raise Exception("The uploaded file is not a valid ZIP archive")
                except Exception as e:
                    logger.error(f"Error extracting ZIP file: {str(e)}")
                    raise Exception(f"Failed to extract ZIP file: {str(e)}")
                
            # Handle spec.js file upload
            elif file.file_extension.lower() == '.spec.js':
                # Determine if we should put this in a ZIP-extracted folder or base tests folder
                target_folder = base_tests_folder
                
                # Check if there's an extracted ZIP folder we should use
                extracted_folders = [
                    f for f in os.listdir(base_tests_folder) 
                    if f.startswith('playwright_tests_') and os.path.isdir(os.path.join(base_tests_folder, f))
                ]
                
                if extracted_folders:
                    # Use the most recent extracted folder
                    target_folder = os.path.join(base_tests_folder, extracted_folders[-1])
                
                # Ensure the filename ends with .spec.js
                if not decoded_filename.endswith('.spec.js'):
                    decoded_filename = f"{decoded_filename.split('.')[0]}.spec.js"
                
                # Save the spec.js file
                file_path = os.path.join(target_folder, decoded_filename)
                
                # Ensure the directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'wb') as f:
                    f.write(decoded_content)
                
                relative_path = os.path.relpath(file_path, base_tests_folder)
                saved_files.append(relative_path)
                logger.info(f"Saved spec.js file to {file_path}")
            
            else:
                logger.warning(f"Skipping unsupported file type: {file.file_extension}")
                raise Exception(f"Unsupported file type: {file.file_extension}. Only .zip and .spec.js files are accepted")
            
        except Exception as e:
            error_msg = f"Failed to process {file.file_extension} file: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    return saved_files

# [Rest of the functions remain the same until list_files_in_tests_folder]

def list_files_in_tests_folder(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lists all test files in the tests directory and updates state
    Now includes files in subdirectories (from extracted ZIPs)
    """
    try:
        directory = './tests'
        os.makedirs(directory, exist_ok=True)
        
        # Find all .spec.js files recursively
        test_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.spec.js'):
                    relative_path = os.path.relpath(os.path.join(root, file), directory)
                    test_files.append(relative_path)
        
        state["available_files"] = test_files
        state["messages"].append({
            "role": "system",
            "content": f"Found {len(test_files)} test files: {', '.join(test_files)}"
        })
        
    except Exception as e:
        state["error_message"] = f"Error listing files: {str(e)}"
        logger.error(state["error_message"])
    
    return state

def analyze_user_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes user prompt using LLM to determine test execution parameters
    """
    try:
        if not state.get("prompt"):
            raise ValueError("No user prompt provided")
        
        prompt_template = f"""You are a test automation analyzer. Analyze this request and respond in perfect JSON format only:
        
        Available test files: {state.get('available_files', [])}
        User request: {state.get('prompt')}
        
        Respond ONLY with valid JSON in this exact format:
        {{
            "task_type": "generate_data" or "run_tests",
            "selected_files": ["filename1.spec.js", "filename2.spec.js"],
            "data_generation_required": true or false,
            "csv_content": "optional, only if data_generation_required is true",
            "command_type": "optional, suggested command type"
        }}

        Important:
        - Only respond with valid JSON
        - No additional text or explanations
        - Ensure all fields are included
        """
        
        model = ChatGroq(
            temperature=0,
            model_name="llama-3.3-70b-versatile",
            api_key="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"
        )
        
        raw_response = model.invoke(prompt_template).content
        cleaned_response = raw_response.strip().replace('```json', '').replace('```', '').strip()
        response_data = json.loads(cleaned_response)
        
        required_fields = ["task_type", "selected_files", "data_generation_required"]
        for field in required_fields:
            if field not in response_data:
                raise ValueError(f"Missing required field in response: {field}")
        
        state["analysis"] = response_data
        state["selected_files"] = response_data.get("selected_files", [])
        
        if response_data.get("data_generation_required"):
            state["test_content"] = response_data.get("csv_content", "")
        
        state["messages"].append({
            "role": "assistant",
            "content": f"Analysis complete. Task: {response_data.get('task_type')}"
        })
        
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse LLM response: {str(e)}. Raw response: {raw_response}"
        state["error_message"] = error_msg
        logger.error(error_msg)
    except Exception as e:
        state["error_message"] = f"Prompt analysis failed: {str(e)}"
        logger.error(state["error_message"])
    
    return state

def create_and_save_file(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates and saves test data files if needed
    """
    analysis = state.get("analysis", {})
    
    if analysis.get("data_generation_required"):
        try:
            os.makedirs("testdata", exist_ok=True)
            file_path = os.path.join("testdata", "testdata.csv")
            
            with open(file_path, 'w') as file:
                file.write(state.get("test_content", ""))
            
            state["messages"].append({
                "role": "system",
                "content": f"Test data saved to {file_path}"
            })
        except Exception as e:
            state["error_message"] = f"Failed to save test data: {str(e)}"
            logger.error(state["error_message"])
    
    return state

def run_playwright_tests(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes Playwright tests based on analysis
    """
    try:
        analysis = state.get("analysis", {})
        if not analysis or analysis.get("task_type") != "run_tests":
            return state

        selected_files = state.get("selected_files", [])
        if not selected_files:
            raise ValueError("No test files selected for execution")

        test_file = f"tests/{selected_files[0]}"
        user_prompt = state.get("prompt", "").lower()

        command_map = {
            "test all": f"npx playwright test {test_file} --reporter=html",
            "report": "npx playwright show-report",
            "debug": f"npx playwright test {test_file} --debug",
            "ui mode": "npx playwright test --ui",
            "headed": f"npx playwright test {test_file} --headed",
            "webkit": "npx playwright test --project=webkit",
            "firefox": "npx playwright test --project=firefox",
            "chrome": "npx playwright test --project=chromium"
        }

        command = next(
            (cmd for kw, cmd in command_map.items() if kw in user_prompt),
            command_map["test all"]
        )

        result = subprocess.run(
            command,
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )

        state["execution_command"] = command
        state["test_results"] = result.stdout or result.stderr
        
        if result.returncode != 0:
            state["error_message"] = f"Tests failed with exit code {result.returncode}"
            logger.error(f"{state['error_message']}\nCommand: {command}\nError: {result.stderr}")
        else:
            state["messages"].append({
                "role": "system",
                "content": f"Tests executed successfully with command: {command}"
            })

    except subprocess.TimeoutExpired:
        state["error_message"] = "Test execution timed out after 300 seconds"
        logger.error(state["error_message"])
    except Exception as e:
        state["error_message"] = f"Test execution error: {str(e)}"
        logger.error(state["error_message"])
    
    return state

def generate_assistant_response(test_results: str, task_type: str, error_message: str = None) -> str:
    """
    Generates complete assistant response with summary and download instructions
    """
    try:
        model = ChatGroq(
            temperature=0,
            model_name="llama-3.3-70b-versatile",
            api_key="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"
        )
        
        if error_message:
            prompt = f"""
            Create a helpful error message response for the user based on this error:
            Error: {error_message}
            
            Include:
            1. Acknowledge the error occurred
            2. Briefly explain what might have caused it
            3. Suggest possible solutions
            4. Keep it concise (2-3 sentences)
            """
        elif task_type == "run_tests":
            prompt = f"""
            Create a complete assistant response including:
            1. A 2-3 sentence summary of these test results:
               {test_results}
            2. Key findings (pass/fail status, number of tests)
            3. Clear instructions to download full report
            4. Format as a professional message
            
            Example structure:
            "The test execution completed with [summary]. 
            [Key findings]. 
            Click the Download button to view the full report."
            """
        else:  # generate_data
            prompt = f"""
            Create a complete assistant response including:
            1. Confirmation of successful data generation
            2. Brief description of data characteristics
            3. Clear instructions that the CSV file is ready for download
            4. Format as a professional message
            
            Important:
            - Do not include any example URLs or links
            - Just mention that the CSV file is ready for download
            
            Example structure:
            "Test data generation completed successfully. 
            The dataset contains [description]. 
            Your CSV file is ready for download."
            """
        
        return model.invoke(prompt).content
        
    except Exception as e:
        logger.error(f"Response generation failed: {str(e)}")
        if error_message:
            return f"An error occurred: {error_message}. Please try again or check the logs."
        elif task_type == "run_tests":
            return "Test execution completed. Click the Download button to view the full report."
        else:
            return "Test data generation completed. Your CSV file is ready for download."

# ========== WORKFLOW CONFIGURATION ==========
def create_workflow_graph():
    """Creates and configures the LangGraph workflow"""
    workflow = StateGraph(AgentStateDict)
    
    workflow.add_node("list_files", list_files_in_tests_folder)
    workflow.add_node("analyze_prompt", analyze_user_prompt)
    workflow.add_node("create_and_save_file", create_and_save_file)
    workflow.add_node("run_tests", run_playwright_tests)
    
    workflow.add_edge(START, "list_files")
    workflow.add_edge("list_files", "analyze_prompt")
    workflow.add_edge("analyze_prompt", "create_and_save_file")
    workflow.add_edge("create_and_save_file", "run_tests")
    workflow.add_edge("run_tests", END)
    
    return workflow.compile()

# ========== API ENDPOINTS ==========
@app.post("/run_tests", response_model=ChatResponse)
async def execute_tests(request: ChatRequest):
    """
    Main API endpoint for test execution
    """
    try:
        initial_state = {
            "prompt": request.prompt,
            "messages": [],
            "error_message": None
        }
        
        if request.file_content:
            try:
                uploaded_files = upload_files_to_tests_folder(request.file_content)
                initial_state["messages"].append({
                    "role": "system",
                    "content": f"Uploaded {len(uploaded_files)} files"
                })
            except Exception as e:
                logger.error(f"File upload failed: {str(e)}")
                raise HTTPException(400, detail=f"File error: {str(e)}")
        
        workflow = create_workflow_graph()
        final_state = workflow.invoke(initial_state)
        
        chat_history = [
            ChatMessage(
                content=request.prompt,
                role="user",
                name="GuiTestingAgent"
            )
        ]
        
        task_type = final_state.get("analysis", {}).get("task_type", "run_tests")
        error_message = final_state.get("error_message")
        
        if task_type == "run_tests":
            results = final_state.get("test_results", "No results generated")
            command = final_state.get("execution_command", "No command executed")
            raw_content = f"Command executed:\n{command}\n\nRaw Results:\n{results}"
        else:
            data_preview = final_state.get("test_content", "No data generated")[:500] + "... [truncated]"
            raw_content = f"Generated Data Preview:\n{data_preview}"
        
        assistant_content = generate_assistant_response(
            raw_content,
            task_type,
            error_message
        )
        
        chat_history.append(
            ChatMessage(
                content=assistant_content,
                role="assistant",
                name="GuiTestingAgent"
            )
        )
        
        download_url = None
        if not error_message:
            if task_type == "run_tests":
                download_url = "/download/report.html"
            else:
                download_url = "/download/testdata.csv"
        
        return {
            "chat_id": request.id,
            "chat_history": chat_history,
            "download_url": download_url
        }
        
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(500, detail=str(e))

@app.get("/download/report.html")
async def download_report():
    """Endpoint to download test report"""
    report_path = "./playwright-report/index.html"
    if os.path.exists(report_path):
        return FileResponse(report_path, media_type="text/html", filename="test_report.html")
    raise HTTPException(404, detail="Report not found")

@app.get("/download/testdata.csv")
async def download_testdata():
    """Endpoint to download generated test data"""
    data_path = "./testdata/testdata.csv"
    if os.path.exists(data_path):
        return FileResponse(data_path, media_type="text/csv", filename="test_data.csv")
    raise HTTPException(404, detail="Test data not found")

# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)