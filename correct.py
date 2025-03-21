from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from typing_extensions import TypedDict

# Structured output models
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
            model_name="llama3-70b-8192",
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
            command_patterns = {
                "test all": "npx playwright test",
                "report": "npx playwright show-report",
                "debug": "npx playwright test --debug",
                "ui mode": "npx playwright test --ui",
                "headed": "npx playwright test --headed",
                "webkit": "npx playwright test --project=webkit",
                "firefox": "npx playwright test --project=firefox",
                "chrome": "npx playwright test --project=chromium"
            }
            
            command_type = analysis.get("command_type", "test all")
            test_files = " ".join([f"tests/{f}" for f in state.get("selected_files", [])])
            command = f"{command_patterns.get(command_type, command_patterns['test all'])} {test_files}"
            
            test_result = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300
            )
            
            state["test_results"] = test_result.stdout
            state["messages"].append({
                "role": "system",
                "content": f"Test execution completed successfully using command: {command}"
            })
        except Exception as e:
            state["error_message"] = f"Test execution error: {str(e)}"
    
    return state