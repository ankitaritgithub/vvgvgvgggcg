import os
import subprocess
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict
from fastapi import FastAPI, HTTPException

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

class TestRequest(BaseModel):
    prompt: str

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
    except Exception as e:
        state["error_message"] = f"Error listing test files: {str(e)}"
    return state


# def analyze_user_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
#     """Analyzes user prompt with structured output"""
#     try:
#         if not state.get("prompt"):
#             state["error_message"] = "No user prompt provided"
#             return state

#         prompt_template = f"""
#         Analyze the following request and provide a structured response:
        
#         Available test files: {state.get('available_files', [])}
#         User request: {state.get('prompt')}

#         Determine if this is a data generation request or a test execution request.
#         For data generation, provide CSV format.
#         For test execution, select relevant test files and command type.
        
#         Respond in the following JSON format:
#         {{
#             "task_type": "generate_data" or "run_tests",
#             "selected_files": [],
#             "data_generation_required": true/false,
#             "csv_content": "optional csv content",
#             "command_type": "optional command type"
#         }}
#         """

#         model = ChatGroq(
#             temperature=0,
#             model_name="llama3-70b-8192",
#             api_key="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"
#         )
        
#         # Get structured response
#         structured_model = model.with_structured_output(TestAnalysisResponse)
#         response = structured_model.invoke(prompt_template)
        
#         # Handle the response safely
#         if response is None:
#             state["error_message"] = "Failed to get response from model"
#             return state
            
#         # Convert response to dict safely
#         try:
#             response_dict = response.dict()
#         except AttributeError:
#             # If response doesn't have dict() method, create a default response
#             response_dict = {
#                 "task_type": "generate_data",
#                 "selected_files": [],
#                 "data_generation_required": True,
#                 "csv_content": "",
#                 "command_type": None
#             }
        
#         # Update state based on structured response
#         state["analysis"] = response_dict
#         state["selected_files"] = response_dict.get("selected_files", [])
        
#         if response_dict.get("data_generation_required"):
#             state["test_content"] = response_dict.get("csv_content", "")
#         else:
#             state["command_type"] = response_dict.get("command_type")
            
#         if "messages" not in state:
#             state["messages"] = []
#         state["messages"].append({
#             "role": "assistant",
#             "content": f"Analysis complete. Task type: {response_dict.get('task_type')}"
#         })
        
#     except Exception as e:
#         state["error_message"] = f"Error analyzing prompt: {str(e)}"
#     return state








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

@app.post("/run_tests")
async def run_tests(request: TestRequest):
    """API endpoint to handle test execution requests."""
    try:
        workflow = create_workflow_graph()
        
        # Initialize state
        initial_state = {
            "prompt": request.prompt,
            "available_files": None,
            "selected_files": None,
            "test_results": None,
            "analysis": None,
            "messages": [],
            "error_message": None
        }
        
        final_state = workflow.invoke(initial_state)
        
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
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
