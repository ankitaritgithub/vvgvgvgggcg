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
    analysis: Optional[str]
    test_content: Optional[str]
    messages: List[Dict[str, str]]
    error_message: Optional[str]
    action_type: Optional[str]
    test_mode: Optional[str]

class TestRequest(BaseModel):
    prompt: str

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

def analyze_user_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes user prompt to determine the required task with structured output
    
    Returns:
    - action_type: 'generate_csv' or 'run_tests'
    - details: Structured information about the task
    """
    try:
        if not state.get("prompt"):
            state["error_message"] = "No user prompt provided"
            return state

        # Initialize the model for structured analysis
        model = ChatGroq(
            temperature=0,
            model_name="llama3-70b-8192",
            api_key="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"
        )

        # Create a structured prompt template
        prompt_template = f"""
        Task Classification and Analysis:
        1. Determine if the user request is for:
           a) Generating test data (CSV generation)
           b) Running Playwright tests
        
        2. If generating CSV:
           - Extract specific details for CSV generation
           - Ensure output is pure CSV format
        
        3. If running tests:
           - Identify most relevant test files
           - Determine test execution mode (all, debug, specific browser, etc.)

        Available test files: {state.get('available_files', [])}
        User request: {state.get('prompt')}

        Respond with a structured JSON-like output containing:
        {{
            "action_type": "generate_csv" or "run_tests",
            "details": {{
                "selected_files": [],
                "test_mode": "",
                "csv_columns": [],
                "additional_instructions": ""
            }}
        }}
        """

        # Invoke the model with structured output
        response = model.invoke(prompt_template)
        
        # Parse the response
        try:
            parsed_response = eval(response.content)
        except Exception as e:
            # Fallback parsing if direct eval fails
            parsed_response = {
                "action_type": "run_tests" if "test" in state.get("prompt", "").lower() else "generate_csv",
                "details": {
                    "selected_files": state.get('available_files', [])[:1],
                    "test_mode": "default",
                    "csv_columns": [],
                    "additional_instructions": response.content
                }
            }

        # Update state based on parsed response
        state["action_type"] = parsed_response.get("action_type", "run_tests")
        state["selected_files"] = parsed_response["details"].get("selected_files", [])
        state["test_content"] = parsed_response["details"].get("csv_columns", [])
        state["test_mode"] = parsed_response["details"].get("test_mode", "default")
        state["analysis"] = str(parsed_response)

        # Add message to state
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append({
            "role": "assistant",
            "content": f"Analysis complete. Action: {state['action_type']}, Selected Files: {state['selected_files']}"
        })

    except Exception as e:
        state["error_message"] = f"Error analyzing prompt: {str(e)}"
    
    return state

def create_and_save_file(state: Dict[str, Any]) -> Dict[str, Any]:
    """Create the folder 'testdata' and file 'testdata.csv', write content, 
    then remove first two lines and update the file."""
    try:
        folder_name = "testdata"
        file_path = os.path.join(folder_name, "testdata.csv")
        
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            print(f"Created folder: {folder_name}")
        
        with open(file_path, 'w') as file:
            file.write(state.get("test_content", ""))
        
        with open(file_path, 'r') as file:
            lines = file.readlines()
        
        if len(lines) > 2:
            lines = lines[2:]
        else:
            lines = []
        
        with open(file_path, 'w') as file:
            file.writelines(lines)
        
        print(f"File processed and updated: {file_path}")
    
    except Exception as e:
        print(f"File handling error: {e}")
    
    return state

def run_playwright_tests(state: Dict[str, Any]) -> Dict[str, Any]:
    """Executes Playwright tests based on selected files and user prompt."""
    if not state.get("selected_files"):
        state["error_message"] = "No test files selected for execution"
        return state

    try:
        user_prompt = state.get("prompt", "").lower()
        print(user_prompt)
        test_file = f"tests/{state['selected_files'][0]}"
        print(test_file)
        
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
        
        command = None
        for pattern, cmd in command_patterns.items():
            if pattern in user_prompt:
                command = cmd
                break
        
        if not command:
            command = command_patterns["test all"]
        
        print(f"Executing Playwright command: {command}")
        
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
    except subprocess.CalledProcessError as e:
        state["error_message"] = f"Test execution failed: {e.stderr}"
    except subprocess.TimeoutExpired as e:
        state["error_message"] = f"Test execution timed out after 300 seconds"
    except Exception as e:
        state["error_message"] = f"Unexpected error during test execution: {str(e)}"
    return state

def create_workflow_graph():
    """Creates the workflow graph with conditional routing"""
    graph = StateGraph(AgentStateDict)
    
    # Add nodes
    graph.add_node("list_files", list_files_in_tests_folder)
    graph.add_node("analyze_prompt", analyze_user_prompt)
    graph.add_node("create_and_save_file", create_and_save_file)
    graph.add_node("run_tests", run_playwright_tests)
    
    # Conditional edges based on action_type
    graph.add_conditional_edges(
        "analyze_prompt",
        lambda state: state.get("action_type"),
        {
            "generate_csv": "create_and_save_file",
            "run_tests": "run_tests"
        }
    )
    
    # Rest of the workflow remains the same
    graph.add_edge(START, "list_files")
    graph.add_edge("list_files", "analyze_prompt")
    graph.add_edge("create_and_save_file", END)
    graph.add_edge("run_tests", END)
    
    return graph.compile()

@app.post("/run_tests")
async def run_tests(request: TestRequest):
    """API endpoint to handle test execution requests."""
    try:
        workflow = create_workflow_graph()
        
        # Initialize state as a dictionary
        initial_state = {
            "prompt": request.prompt,
            "available_files": None,
            "selected_files": None,
            "test_results": None,
            "analysis": None,
            "messages": [],
            "error_message": None,
            "action_type": None,
            "test_mode": None
        }
        
        final_state = workflow.invoke(initial_state)
        
        return {
            "status": "success" if not final_state.get("error_message") else "error",
            "available_files": final_state.get("available_files"),
            "selected_files": final_state.get("selected_files"),
            "analysis": final_state.get("analysis"),
            "test_results": final_state.get("test_results"),
            "messages": final_state.get("messages"),
            "action_type": final_state.get("action_type"),
            "test_mode": final_state.get("test_mode"),
            "error": final_state.get("error_message")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)