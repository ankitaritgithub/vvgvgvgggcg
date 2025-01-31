import os
import subprocess
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.tools import tool
import uuid
from pydantic import BaseModel
from typing import List


class Credential(BaseModel):
    email: str
    password: str



test_cases = []

def get_test_case(query: str):
    """Fetch the test case based on the user query from a dictionary."""
    test_cases = {
        "login":"test_login",
        "valid": "valid_login",
        "debug": "test_debug",
        "ui": "test_ui",
        "headed": "test_headed",
        "invalid": "invalid_login",
        "credential": "login_with_credential",
        "generated details": "login_with_csv",
        "report" : "test_report",
        "default": "test_default"
    }
    
    if query.lower() in test_cases:
        # print(f"Found test case: {test_cases[query.lower()]}")
        return test_cases[query.lower()]
    
    for key in test_cases:
        if key.lower() in query.lower():
            print(f"Found test case via partial match: {test_cases[key]}")
            return test_cases[key]
    
    print("No matching test case found. Using default.")
    return test_cases["default"]


@tool
def create_and_save_file(testdata: str, content: str, mode: str = 'w'):
    """Create the folder 'testdata' and a file 'testdata.csv',
       open it once, write the content, and then close it."""
    
    try:
        # Ensure the folder structure exists
        folder_name = os.path.dirname(f"testdata/{testdata}")
        if folder_name and not os.path.exists(folder_name):
            os.makedirs(folder_name)
            print(f"The folder '{folder_name}' was created.")
        
        # Define the file path
        file_path = os.path.join(folder_name, testdata)

        # Check if the file exists before proceeding
        if os.path.exists(file_path) and mode == 'w':
            print(f"File '{file_path}' already exists. Overwriting content.")
        
        # Open file once, write content, and automatically close it
        with open(file_path, mode) as file:
            file.write(content)
        
        # Confirmation message
        print(f"Content has been successfully written to '{file_path}'")

    except Exception as e:
        print(f"An error occurred while handling the file: {e}")


@tool
def run_playwright_commands(query: str, credentials: List[Credential]):
    """Search for specific commands based on user input."""
    test_case = get_test_case(query)
    print(f"Test case '{test_case}' detected. Running corresponding Playwright Tests...")

    commands = {
        "valid_login": {
            "test_command": "npx playwright test tests/test.spec.js"
        },
        "test_headed": {
            "test_command": "npx playwright test --headed"
        },
        "test_debug": {
            "test_command": "npx playwright test --debug"
        },
        "invalid_login": {
            "test_command": "npx playwright test tests/invalidlogin.spec.js"
        },
        "test_ui": {
            "test_command": "npx playwright test --ui"
        },
        "test_login": {
            "test_command": "npx playwright test --reporter=list"
        },
        "login_with_credential":{
            "test_command": "npx playwright test tests/test2.spec.js --reporter=list"
        },
        "login_with_csv" : {
            "test_command": "npx playwright test tests/csvlogin.spec.js --reporter=list"
        },
        "test_report": {
            "test_command": "npx playwright test --reporter=html",
            "report_command": "npx playwright show-report"
        },
        "test_json": {
            "test_command": "PLAYWRIGHT_JSON_OUTPUT_NAME=results.json npx playwright test --reporter=json"
        }
    }

    try:
        if test_case == "default":
            try:
                response = model.invoke(f"The test case for query '{query}' does not exist. Please provide guidance on what kind of test should be created for this scenario.")
                print("\nTest case not found. Model suggestion:")
                print(response.content)
                return
            except Exception as e:
                print(f"\nError getting model suggestion: {e}")
                print("Please try a different test case or check the available test cases.")
                return
            

        if test_case == "login_with_credential":
            os.makedirs('tests', exist_ok=True)
            print(f"Running login test with email: {credentials[0].email}, password: {credentials[0].password}")
            test_content = f"""
import {{ test, expect }} from '@playwright/test';

test('login test', async ({{ page }}) => {{
    await page.goto('https://dev.typ.delivery/en/auth/login');
    await page.getByPlaceholder('Email').fill('{credentials[0].email}');
    await page.getByPlaceholder('Password').fill('{credentials[0].password}');
    await page.getByRole('button', {{ name: 'Sign in' }}).click();
}});
"""

            test_file = os.path.join('tests', 'test2.spec.js')
            with open(test_file, 'w') as f:
                f.write(test_content)
                print("Test file written successfully.")
            
            test_command = commands[test_case]["test_command"]
            print(f"Executing command: {test_command}")
            try:
                subprocess.run(test_command, shell=True, check=True, stderr=subprocess.PIPE, timeout=300)
                print("Playwright test executed successfully!")
            except subprocess.CalledProcessError as e:
                print(f"An error occurred while running the test: {str(e)}")

        else:
            command = commands.get(test_case)
            if not command:
                print(f"\nError: Test case '{test_case}' not found in commands.")
                return

            try:
                test_result = subprocess.run(command["test_command"], shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
                print("Playwright Tests completed successfully!")
                print("Output:\n", test_result.stdout.decode())
                
                if "report_command" in command:
                    print("\nOpening Playwright HTML Report...")
                    subprocess.Popen(command["report_command"], shell=True)
                    print("HTML Report command executed successfully!")

            except subprocess.CalledProcessError as e:
                print("\nError occurred during execution:")
                # print(f"Command: {e.cmd}")
                print(f"Return Code: {e.returncode}")
                print(f"Standard Output:\n{e.stdout.decode()}")
                print(f"Error Message:\n{e.stderr.decode()}")
            except subprocess.TimeoutExpired as e:
                print(f"\nCommand timed out: {e.cmd}")
            except Exception as e:
                print(f"\nAn unexpected error occurred: {e}")

    except subprocess.CalledProcessError as e:
        print("\nError occurred during execution:")
        # print(f"Command: {e.cmd}")
        print(f"Return Code: {e.returncode}")
        print(f"Standard Output:\n{e.stdout.decode()}")
        print(f"Error Message:\n{e.stderr.decode()}")
    except subprocess.TimeoutExpired as e:
        print(f"\nCommand timed out: {e.cmd}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

    return True

# Define tools

tools = [run_playwright_commands , create_and_save_file]

# api_key = os.getenv("api_key", "AIzaSyBIS1dgPIe3H2xuWCDvn6bcsz-n3-Ba2vg")
# model_name = os.getenv("LLM_MODEL", "gemini-1.5-pro-002")  
# server_url = os.getenv("PROXY_SERVER_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-002:generateContent")

try:
    # model = ChatGoogleGenerativeAI(
    #     model=model_name, 
    #     temperature=0,
    #     api_key=api_key,
    #     PROXY_SERVER_URL=server_url
    # )
    model = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile" , api_key="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")
except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    print("Please check your Gemini API key and try again.")
    exit(1)

checkpointer = MemorySaver()
app = create_react_agent(model, tools, checkpointer=checkpointer)

while True:
    try:
        query = input("Please enter your query or type 'exit' to quit: ")
        if query.lower() == "exit":
            print("Exiting the application...")
            break
       
#         You are a quality assurance agent responsible for running available test cases and generating test data based on user queries. 
# Available test cases include: 'login', 'debug', 'ui', 'headed', 'invalid', 'valid', 'report', 'login with credential', 'login with csv', and 'json'.
# Process the query and use the appropriate tools to execute the test case. If the user queries for login with credential tests, take credentials as input and proceed accordingly
        
        # Call the model and get the response
        try:
            final_state = app.invoke(
                {"messages": [
                    {
                        "role": "system",
                        "content": """You are a intelligent agent so route the queries accordingly to different tools once this create_and_save_file is used based on queries exit from the loop .
                        
                        Available test cases include: 'login', 'debug', 'ui', 'headed', 'invalid', 'valid', 'report', 'credential', 'generated details', and 'json'.
                        Process the query and use the appropriate tools to execute the test case. and And if user query to login with credential tests, take credentials as input.
                        Process the query and use the appropriate tools to execute the test case.
   
                        """
                    },
                    {"role": "user", "content": query}
                ]},
                config={"configurable": {"thread_id": str(uuid.uuid4())}}
            )
            
        except Exception as invoke_error:
            print(f"Error invoking the model: {invoke_error}")
            continue 
        
        # Check if the response from the model is empty or invalid
        if not final_state["messages"] or not final_state["messages"][-1].content.strip():
            print("Error: The model's response is empty or invalid. Please check the query or model configuration.")
        else:
            print("Generated Text:", final_state["messages"][-1].content)

    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")
        break
    except Exception as e:
        print(f"An error occurred: {e}")
