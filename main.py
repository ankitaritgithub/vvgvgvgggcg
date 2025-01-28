import os
import subprocess
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
import uuid

test_case = []
def get_test_case(query: str):
    """Fetch the test case based on the user query from a dictionary."""
    test_cases = {
        "valid": "valid_login",
        "debug": "test_debug",
        "ui": "test_ui",
        "headed": "test_headed",
        "invalid": "invalid_login",
        "login": "test_login",
        "default": "test_default"
    }
    
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
        "valid_login": {
            "test_command": "npx playwright test tests/test.spec.js"
        },
        "test_login": {
            "test_command": "npx playwright test"
        },
        "test_debug": {
            "test_command": "npx playwright test --debug"
        },
        "test_ui": {
            "test_command": "npx playwright test --ui"
        },
        "test_headed": {
            "test_command": "npx playwright test --headed"
        },
        "invalid_login": {
            "test_command": "npx playwright test tests/test-1.spec.js"
        },
        "test_default": {
            "test_command": "npx playwright test --reporter=html"
        }
    }

    command = commands.get(test_case, commands["test_default"])

    try:
        test_result = subprocess.run(command["test_command"], shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        print("Playwright Tests completed successfully!")
        print("Output:\n", test_result.stdout.decode())
        # print("Errors:\n", test_result.stderr.decode())
        
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

    return True

tools = [run_playwright_commands]
api_key = os.getenv("GEMINI_API_KEY", "AIzaSyAtIYbldVqhfnGPVJtm46GjKeF-yRrFC-Q")
model = ChatGoogleGenerativeAI(model="gemini-1.5-pro-002", temperature=0, api_key=api_key)
checkpointer = MemorySaver()
app = create_react_agent(model, tools, checkpointer=checkpointer)
while True:
    try:
        user_query = input("Please enter your query prompt  or type 'exit' to quit: ")
        if user_query.lower() == "exit":
            print("Exiting the application...")
            break
        final_state = app.invoke(
            {"messages": [
                {"role": "system", "content": "You are a quality assurance agent responsible for running available test cases based on user queries. Available test cases include: 'login', 'debug', 'ui', 'headed', 'invalid' ,'valid' and 'default'. Process the query and use the run_playwright_commands tool to execute the appropriate test case."},
                {"role": "user", "content": user_query}
            ]},
            config={"configurable": {"thread_id": str(uuid.uuid4())}}
        )
        print(final_state["messages"][-1].content)
    
    except Exception as e:
        print(f"An error occurred: {e}")
 































































































# import os
# import requests
# from langgraph.prebuilt import create_react_agent
# from langgraph.checkpoint.memory import MemorySaver
# from langchain_anthropic import ChatAnthropic
# # from langgraph import tool
# from langchain_core.tools import tool
# from langchain_google_genai import ChatGoogleGenerativeAI 


# @tool
# def search(query: str):
#     """Return a weather update for San Francisco or other locations."""
#     if "sf" in query.lower() or "san francisco" in query.lower():
#         return "It's 60 degrees and foggy."
#     return "It's 90 degrees and sunny."

# tools = [search]

# api_key = os.getenv("GEMINI_API_KEY", "AIzaSyAtIYbldVqhfnGPVJtm46GjKeF-yRrFC-Q")  

# model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0, api_key=api_key)

# checkpointer = MemorySaver()

# app = create_react_agent(model, tools, checkpointer=checkpointer)

# try:
#     final_state = app.invoke(
#         {"messages": [{"role": "user", "content": "what is the weather in sf"}]},
#         config={"configurable": {"thread_id": 42}}
#     )
#     print(final_state["messages"][-1].content)
# except Exception as e:
#     print(f"An error occurred: {e}")
