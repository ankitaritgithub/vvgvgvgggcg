import streamlit as st
import requests
import json
from time import sleep

st.set_page_config(
    page_title="Your App Title",
    page_icon=":smiley:",
    layout="wide"
)

# Configuration
BACKEND_URL = "http://localhost:8000/run_tests"

def main():
    st.title("🚀 Agent QA")
    st.markdown("### AI-Powered Test Automation")
    
    # User input section
    with st.form(key="test_request_form"):
        prompt = st.text_area(
            "Enter your test request:",
            placeholder="e.g., 'Run all tests in headed mode' or 'Generate test data for login scenarios'",
            height=100
        )
        submit_button = st.form_submit_button("Execute Request")
    
    if submit_button and prompt:
        with st.spinner("🧠 Processing your request..."):
            try:
                response = requests.post(
                    BACKEND_URL,
                    json={"prompt": prompt},
                    timeout=300
                )
                
                if response.status_code != 200:
                    st.error(f"API Error: {response.text}")
                    return
                
                data = response.json()
                
                # Display results
                st.success("✅ Request processed successfully!")
                
                # Results container
                with st.container():
                    # Error display
                    if data.get("error"):
                        st.error(f"❌ Error: {data['error']}")
                        return
                    
                    # Quick overview columns
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Task Type", data.get("analysis", {}).get("task_type", "N/A"))
                    with col2:
                        st.metric("Files Selected", len(data.get("selected_files", [])))
                    with col3:
                        st.metric("Data Generated", "Yes" if data.get("test_content") else "No")
                    
                    # Detailed sections
                    with st.expander("📄 Detailed Messages Log", expanded=True):
                        for msg in data.get("messages", []):
                            st.write(f"**{msg['role'].title()}:** {msg['content']}")
                    
                    if data.get("available_files"):
                        with st.expander("📁 Available Test Files"):
                            st.write(data["available_files"])
                    
                    if data.get("selected_files"):
                        with st.expander("✅ Selected Test Files"):
                            st.write(data["selected_files"])
                    
                    if data.get("analysis"):
                        with st.expander("🔍 Analysis Details"):
                            analysis = data["analysis"]
                            st.json({
                                "Task Type": analysis.get("task_type"),
                                "Data Generation Required": analysis.get("data_generation_required"),
                                "Command Type": analysis.get("command_type")
                            })
                    
                    if data.get("test_results"):
                        with st.expander("📊 Test Results"):
                            st.code(data["test_results"], language="text")
                    
                    if data.get("test_content"):
                        with st.expander("📁 Generated Test Data"):
                            st.code(data["test_content"], language="csv")
                
            except requests.exceptions.RequestException as e:
                st.error(f"🔌 Connection Error: {str(e)}")
            except json.JSONDecodeError:
                st.error("❌ Invalid response from server")

def sidebar():
    with st.sidebar:
        st.markdown("## About")
        st.markdown("""
        This dashboard enables AI-powered test automation using:
        - **Playwright** for browser automation
        - **Groq/Llama3** for natural language processing
        - **FastAPI** backend processing
        """)
        
        st.markdown("## How to Use")
        st.markdown("""
        1. Enter your request in natural language
        2. Examples:
           - "Run all login tests in Chrome"
           - "Debug the checkout tests"
           - "Generate test data for user registration"
        3. View results in real-time
        """)
        
        st.markdown("## Status")
        try:
            response = requests.get(BACKEND_URL.replace("/run_tests", "/"))
            if response.status_code == 200:
                st.success("✅ Backend connected")
            else:
                st.error("❌ Backend unavailable")
        except:
            st.error("❌ Backend connection failed")

if __name__ == "__main__":
    sidebar()
    main()