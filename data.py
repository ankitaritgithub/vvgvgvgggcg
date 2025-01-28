import os
import subprocess
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
import uuid


@tool
def get_user_credentials(query: str = "") -> dict:
    """Get user email and password through interactive prompts."""
    email = input("Please enter your email: ")
    password = input("Please enter your password: ")
    return {"email": email, "password": password}

test_cases = []
def get_test_case(query: str):
    """Fetch the test case based on the user query from a dictionary."""
    test_cases = {
        "valid": "valid_logins",
        "debug": "test_debug",
        "ui": "test_ui",
        "headed": "test_headed",
        "invalid": "invalid_login",
        "login": "test_login",
        "report": "test_report",
        "json": "test_json",
    }

    if query.lower() in test_cases:
        return test_cases[query.lower()]
    
    for key in test_cases:
        if key.lower() in query.lower():
            return test_cases[key]
    
    return test_cases["default"]


@tool
def run_playwright_commands(query: str):
    """Search for specific commands based on user input."""
    test_case = get_test_case(query)
    print(f"Test case '{test_case}' detected. Running corresponding Playwright Tests...")

    commands = {
        "valid_logins": {
            "test_command": "npx playwright test tests/test.spec.js"
        },
        "test_headed": {
            "test_command": "npx playwright test --headed"
        },
        "test_debug": {
            "test_command": "npx playwright test --debug"
        },
        "invalid_login": {
            "test_command": "npx playwright test tests/test1.spec.js"
        },
        "test_ui": {
            "test_command": "npx playwright test --ui"
        },
        "test_login": {
            "test_command": "npx playwright test --reporter=list"
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

        if test_case == "test_login":
            print("Running login test...")

            os.makedirs('tests', exist_ok=True)

            credentials = get_user_credentials.invoke(input="")
            email = credentials["email"]
            password = credentials["password"]
            
            print(f"Running login test with email: {email}, password: {password}")

            test_content = f"""
import {{ test, expect }} from '@playwright/test';

test('login test', async ({{ page }}) => {{
    await page.goto('https://dev.typ.delivery/en/auth/login');
    await page.getByPlaceholder('Email').fill('{email}');
    await page.getByPlaceholder('Password').fill('{password}');
    await page.getByRole('button', {{ name: 'Sign in' }}).click();
}});
"""

            test_file = os.path.join('tests', 'test2.spec.js')
            with open(test_file, 'w') as f:
                f.write(test_content)

            test_command = commands[test_case]["test_command"]
            subprocess.run(test_command.split())

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
                print(f"Command: {e.cmd}")
                print(f"Return Code: {e.returncode}")
                print(f"Standard Output:\n{e.stdout.decode()}")
                print(f"Error Message:\n{e.stderr.decode()}")
            except subprocess.TimeoutExpired as e:
                print(f"\nCommand timed out: {e.cmd}")
            except Exception as e:
                print(f"\nAn unexpected error occurred: {e}")

    except subprocess.CalledProcessError as e:
        print("\nError occurred during execution:")
        print(f"Command: {e.cmd}")
        print(f"Return Code: {e.returncode}")
        print(f"Standard Output:\n{e.stdout.decode()}")
        print(f"Error Message:\n{e.stderr.decode()}")
    except subprocess.TimeoutExpired as e:
        print(f"\nCommand timed out: {e.cmd}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


tools = [run_playwright_commands, get_user_credentials]

api_key = os.getenv("api_key", "AIzaSyBmUrLDjqOzlrpVMUuYKxX00Mb_wdkq34Y")
model_name = os.getenv("LLM_MODEL", "gemini-1.5-flash")  
server_url = os.getenv("PROXY_SERVER_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-002:generateContent")

# print(f"we are using this API Key: {api_key}")
# print(f"Hello you are using thisModel Name: {model_name}")
# print(f"which is running on this Server URL: {server_url}")

try:
    model = ChatGoogleGenerativeAI(
        model=model_name, 
        temperature=0,
        api_key=api_key,
        PROXY_SERVER_URL=server_url
    )
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
        final_state = app.invoke(
            {"messages": [
                {"role": "system", "content": "You are a quality assurance agent responsible for running available test cases based on user queries. Available test cases include: 'login', 'debug', 'ui', 'headed', 'invalid', 'valid', 'report' and 'json'. For login-related tests, you should use the get_user_credentials tool to collect user information before running the test. Process the query and use the appropriate tools to execute the test case."},
                {"role": "user", "content": query}
            ]},
            config={"configurable": {"thread_id": str(uuid.uuid4())}}
        )
        print(final_state["messages"][-1].content)
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")
        break
    except Exception as e:
        print(f"An error occurred: {e}")
