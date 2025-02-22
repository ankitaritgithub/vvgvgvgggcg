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
    messages: List[Dict[str, str]]
    error_message: Optional[str]  

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
    """Analyzes user prompt to identify relevant test files and command patterns."""
    try:
        if not state.get("prompt"):
            state["error_message"] = "No user prompt provided"
            return state

        prompt_template = f"""
        Analyze the user's request to determine the test execution details.

        Available test files: {state.get('available_files', [])}
        User request: {state.get('prompt')}


        Task:
        1. Please analyze the request and select the most relevant test files from the available list as per user's request.
        2. based on user_prompt and selected files, execute the command as per the user prompt request.
        3. If the request doesn't specify a particular test, select all available test files
        
        Return your response in this exact format:
        Reasoning: [brief explanation]
        """

        model = ChatGroq(
            temperature=0,
            model_name="llama3-70b-8192",
            api_key="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"
        )
        
        response = model.invoke(prompt_template)
        print(response)
        
        # Parse the response to extract selected files
        selected_files = []
        print(selected_files ,"***************************************")
        for file in state.get('available_files', []):
            if file in response.content:
                selected_files.append(file)
                print(file)
        
        state["selected_files"] = selected_files
        state["analysis"] = response.content
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append({
            "role": "assistant",
            "content": f"Analysis complete. Selected files: {', '.join(selected_files)}"
        })
    except Exception as e:
        state["error_message"] = f"Error analyzing prompt: {str(e)}"
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
    """Creates the workflow graph with the new execution flow."""
    graph = StateGraph(AgentStateDict)
    
    # Add nodes
    graph.add_node("list_files", list_files_in_tests_folder)
    graph.add_node("analyze_prompt", analyze_user_prompt)
    graph.add_node("run_tests", run_playwright_tests)
    
    # Define the new flow
    graph.add_edge(START, "list_files")
    graph.add_edge("list_files", "analyze_prompt")
    graph.add_edge("analyze_prompt", "run_tests")
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