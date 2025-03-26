def run_playwright_tests(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Playwright tests after navigating to the extracted directory"""
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
            
            # Define the target directory path
            target_dir = os.path.expanduser(
                "~/Desktop/zipfile/GUIagentTask/gui_testing_agent/extractedplaywrightscript/zipfile/"
            )
            
            # Verify the target directory exists
            if not os.path.exists(target_dir):
                raise Exception(f"Target directory does not exist: {target_dir}")
            
            # Store the original working directory
            original_dir = os.getcwd()
            
            try:
                # Change to the target directory
                os.chdir(target_dir)
                print(f"Changed working directory to: {os.getcwd()}")
                
                # Get the user prompt from state
                user_prompt = state.get("prompt", "").lower()

                # Initialize command as None
                command = None

                # Define command patterns dictionary
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
                
                # Determine the base command based on user prompt
                for keyword, cmd in command_patterns.items():
                    if keyword in user_prompt:
                        command = cmd
                        break
                
                if not command:
                    command = command_patterns["test all"]
                
                # If specific test file is selected, add it to the command
                if selected_files and "test all" not in user_prompt.lower():
                    command = f"{command} {selected_files[0]}"
                
                print(f"Executing Playwright command: {command}")
                print(f"Current directory: {os.getcwd()}")
                
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
                

                
            finally:
                # Always return to the original directory
                os.chdir(original_dir)
                print(f"Restored working directory to: {original_dir}")
            
        except subprocess.CalledProcessError as e:
            state["error_message"] = f"Test execution failed: {e.stderr}"
        except subprocess.TimeoutExpired as e:
            state["error_message"] = f"Test execution timed out after 300 seconds"
        except Exception as e:
            state["error_message"] = f"Test execution error: {str(e)}"
    
    return state
******************************************************
def run_playwright_tests(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Playwright tests after navigating to the extracted directory"""
    analysis = state.get("analysis", {})
    if not isinstance(analysis, dict):
        analysis = analysis.dict()
    
    if analysis.get("task_type") == "run_tests":
        # Store the original working directory at the start
        original_dir = os.getcwd()
        print(f"Original working directory: {original_dir}")
        
        try:
            # Get selected files first
            selected_files = state.get("selected_files", [])
            if not selected_files:
                state["error_message"] = "No test files selected for execution"
                return state
            
            # Define the target directory path
            target_dir = os.path.expanduser(
                "~/Desktop/zipfile/GUIagentTask/gui_testing_agent/extractedplaywrightscript/zipfile/"
            )
            
            # Verify the target directory exists
            if not os.path.exists(target_dir):
                raise Exception(f"Target directory does not exist: {target_dir}")
            
            # Change to the target directory
            os.chdir(target_dir)
            print(f"Changed to target directory: {os.getcwd()}")
            
            # Get the user prompt from state
            user_prompt = state.get("prompt", "").lower()

            # Initialize command as None
            command = None

            # Define command patterns dictionary
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
            
            # Determine the base command based on user prompt
            for keyword, cmd in command_patterns.items():
                if keyword in user_prompt:
                    command = cmd
                    break
            
            if not command:
                command = command_patterns["test all"]
            
            # If specific test file is selected, add it to the command
            if selected_files and "test all" not in user_prompt.lower():
                command = f"{command} {selected_files[0]}"
            
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
        finally:
            # Always return to the original directory
            os.chdir(original_dir)
            print(f"Restored original working directory: {os.getcwd()}")
    
    return state
