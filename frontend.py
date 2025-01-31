import streamlit as st
import requests
import json
from typing import Dict, List

# FastAPI backend URL
FASTAPI_URL = "http://localhost:8000"

def main():
    st.set_page_config(
        page_title="Agent QA",
        page_icon="🎭",
        layout="wide"
    )
    
    st.title("🎭 Agent QA")
    st.markdown("---")

    # Create two columns for better layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Test Configuration")
        
        # Query input method selection
        query_method = st.radio(
            "Choose Query Method",
            ["Predefined Tests", "Custom Prompt"],
            horizontal=True
        )
        
        if query_method == "Predefined Tests":
            # Test case selection
            test_cases = {
                "login": "Basic Login Test",
                "valid": "Valid Login Test",
                "debug": "Debug Mode Test",
                "ui": "UI Components Test",
                "headed": "Headed Mode Test",
                "invalid": "Invalid Login Test",
                "credential": "Login with Credentials",
                "generated details": "Login with CSV Data",
                "report": "Generate Test Report",
                "default": "Default Test Suite"
            }
            
            selected_test = st.selectbox(
                "Select Test Case",
                options=list(test_cases.keys()),
                format_func=lambda x: f"{x} - {test_cases[x]}"
            )
            query = selected_test
        else:
            # Custom query input
            query = st.text_area(
                "Enter Your Query",
                placeholder="Example: Run a login test with debug mode enabled",
                help="Enter any natural language query describing the test you want to run"
            )

        # Credential input section
        use_credentials = st.checkbox("Use Custom Credentials")
        credentials: List[Dict[str, str]] = []
        
        if use_credentials:
            with st.expander("Credential Details", expanded=True):
                email = st.text_input("Email", placeholder="Enter email")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                if email and password:
                    credentials = [{"email": email, "password": password}]

        # Run test button with loading state
        if st.button("🚀 Run Test", type="primary", disabled=not query):
            if not query:
                st.warning("Please enter a query or select a test case before running.")
                return

            with st.spinner("Running test..."):
                try:
                    payload = {"prompt": query}
                    if credentials:
                        payload["credentials"] = credentials
                    
                    response = requests.post(f"{FASTAPI_URL}/langgraph", json=payload)
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Test executed successfully!")
                        
                        # Display Playwright test results in a separate box
                        if 'stdout' in result:
                            with st.container():
                                st.subheader("🎭 Test Results")
                                st.code(result['stdout'], language='text')
                        
                        # Display full results in expandable section
                        with st.expander("Full Test Results", expanded=False):
                            st.json(result)
                            
                            # Add to test history
                            if 'test_history' not in st.session_state:
                                st.session_state.test_history = []
                            st.session_state.test_history.append(f"{query[:50]}... - Success")
                    else:
                        st.error(f"❌ Error: {response.status_code}")
                        try:
                            error_detail = response.json().get('detail', 'Unknown error')
                            st.error(f"Server response: {error_detail}")
                        except:
                            st.error(f"Server response: {response.text}")
                        
                except requests.exceptions.ConnectionError:
                    st.error("""
                    ❌ Connection Error: Could not connect to the backend server
                    
                    **Please check:**
                    1. Is the FastAPI backend running?
                    2. Is it running on the correct port (8000)?
                    3. Are there any firewall issues?
                    """)
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    with col2:
        st.subheader("Quick Help")
        if query_method == "Predefined Tests":
            st.info("""
            **Available Test Types:**
            - Basic Login
            - Valid/Invalid Login
            - UI Component Tests
            - Debug Mode Tests
            - And more...
            """)
        else:
            st.info("""
            **How to Write Queries:**
            1. Be specific about what you want to test
            2. Mention any special conditions
            3. Include test type if known
            
            **Examples:**
            - "Run a login test with debug mode"
            - "Test UI components in headed mode"
            - "Generate a test report for login"
            """)
        
        # Display test history
        st.subheader("Recent Test History")
        if 'test_history' not in st.session_state:
            st.session_state.test_history = []
            
        for test in st.session_state.test_history[-5:]:  # Show last 5 tests
            st.text(test)

if __name__ == "__main__":
    main()