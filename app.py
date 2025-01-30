import os
import subprocess
import streamlit as st
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
import uuid
from pydantic import BaseModel
from typing import List

# Your existing classes and functions here
class Credential(BaseModel):
    email: str
    password: str

test_cases = {}

def get_test_case(query: str):
    """Fetch the test case based on the user query from a dictionary."""
    test_cases = {
        "valid": "valid_login",
        "debug": "test_debug",
        "ui": "test_ui",
        "headed": "test_headed",
        "invalid": "invalid_login",
        "login with credential": "login_with_credential",
        "login with csv": "login_with_csv",
        "default": "test_default"
    }
    
    if query.lower() in test_cases:
        return test_cases[query.lower()]
    
    for key in test_cases:
        if key.lower() in query.lower():
            return test_cases[key]
    
    return test_cases["default"]

@tool
def create_and_save_file(filename: str, content: str, mode: str = 'w'):
    """Create a file if it doesn't exist, open it, write content, and save it."""
    try:
        if not os.path.exists(filename):
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, mode) as file:
            file.write(content)
        return f"Content has been successfully written to '{filename}'"
    except Exception as e:
        return f"An error occurred while handling the file: {e}"

@tool
def run_playwright_commands(query: str, credentials: List[Credential]):
    """Run Playwright commands based on the user's query."""
    test_case = get_test_case(query)
    commands = {
        "valid_logins": {
            "test_command": "npx playwright test tests/test.spec.js"
        },
        "login_with_credential": {
            "test_command": "npx playwright test tests/test2.spec.js --reporter=list"
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
        }
    }

    try:
        if test_case == "login_with_credential":
            test_content = f"""
            import {{ test, expect }} from '@playwright/test';

            test('valid', async ({{ page }}) => {{
                await page.goto('https://dev.typ.delivery/en/auth/login');
                await page.getByPlaceholder('Email').fill('{credentials[0].email}');
                await page.getByPlaceholder('Password').fill('{credentials[0].password}');
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
                return f"Test case '{test_case}' not found."
            subprocess.run(command["test_command"], shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            return "Playwright Tests completed successfully!"

    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.decode()}"
    except Exception as e:
        return f"An error occurred: {e}"

# Initialize Streamlit App
def main():
    st.title("Playwright Test Case Executor")
    
    # Sidebar for query input and credentials (if needed)
    st.sidebar.header("Test Case Settings")
    query = st.sidebar.text_input("Enter your query", "")
    email = st.sidebar.text_input("Email for login tests", "")
    password = st.sidebar.text_input("Password for login tests", "", type="password")

    if query:
        if "login" in query.lower() and email and password:
            credentials = [Credential(email=email, password=password)]
            result = run_playwright_commands(query, credentials)
        else:
            result = run_playwright_commands(query, [])

        st.write(result)

    st.sidebar.write("### Available Queries:")
    st.sidebar.write("- login")
    st.sidebar.write("- debug")
    st.sidebar.write("- ui")
    st.sidebar.write("- headed")
    st.sidebar.write("- invalid")
    st.sidebar.write("- valid")
    st.sidebar.write("- report")
    st.sidebar.write("- login with credential")
    st.sidebar.write("- login with csv")
    st.sidebar.write("- json")

# Running the Streamlit app
if __name__ == "__main__":
    main()
