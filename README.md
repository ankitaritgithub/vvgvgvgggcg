# Project Title

A brief description of what this project does and its purpose.

## Description

This project is designed to [insert description of the project]. It aims to [insert goals or objectives of the project].

## Installation

To install this project, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/ankitaritgithub/dddddddddd.git
   ```
2. Navigate to the project directory:
   ```bash
   cd dddddddddd
   ```

## System Overview

### System Architecture

The system consists of the following components:

* Langraph framework
* Gemini-1.5-pro-002 model
* Playwright test scripts and commands
* Langchain with human-in-the-loop approach
* Streamlit UI for Agent QA

### System Functionality

The system provides the following functionalities:

* Handles user requests and runs Playwright test scripts and commands
* Decides which test to run based on user query
* Runs tests using Playwright and shows results in the terminal
* Generates HTML reports and saves them in VS Code
* Provides detailed reports from multiple browsers in JSON format
* Takes user input and provides responses based on their queries using Agent QA
* Updates script with user-provided email and password and executes it to test login functionality

### System Workflow

Here's a high-level overview of how the system works:

1. User types in a query
2. System decides which test to run
3. System runs the test using Playwright
4. System shows results in the terminal
5. System generates HTML report and saves it in VS Code
6. System provides detailed reports from multiple browsers in JSON format
7. Agent QA takes user input and provides responses based on their queries
8. Agent QA updates script with user-provided email and password and executes it to test login functionality

## How It Works
- The user types in a query, and the system decides which test to run.
- It runs the test using Playwright and shows the results in the terminal.
- The system keeps running until the user types "exit" to stop.

## Test Scenarios
- If the user asks to test valid user login, it only runs the valid login test.
- If the user asks for a login test, it runs both valid and invalid login tests and shows the results, plus an HTML report that can be viewed in the browser and saved in VS Code.
- If the user wants to run in headed mode, it switches to UI mode and runs the test that way.

## Integration with Libraries
- While we could use the Faker library in the Playwright script, I have used Langchain with a human-in-the-loop approach. This means I’ve built a tool that interacts with the script while it’s running, based on what the user asks.
- The system selects a test based on the user's request (login, valid, invalid).

## Reporting
- A report command is included to get detailed reports through the server.
- The HTML report is generated and saved in VS Code.
- When the report is triggered, detailed reports from multiple browsers are generated and displayed visually.
- If the user wants the report in JSON format, running the script across multiple browsers generates a JSON file for further analysis.

## Agent QA Functionality
- I have developed a demo Agent QA that takes user input and provides responses based on their queries, featuring a Streamlit UI.
- User prompts Agent QA to generate 10 random email addresses and passwords for login functionality.
- Agent QA creates a folder using the available tools, and the required data is generated in the created folder.

## User Input Handling
- User provides their own login credentials.
- Agent QA updates the script with the user-provided email and password, and the updated script is executed to test the login functionality.

## Video Demonstrations

- [Demo 1: Agent QA with Playwright](https://example.com/demo1)
- [Playwright Test 1](https://example.com/playwright-test1)
- [Dynamic Data Demonstration](https://example.com/dynamic-data-demo)
- [Reporters in Playwright](https://example.com/reporters-in-playwright)
- [Chat Agent QA - Microsoft Teams Screenshot](https://example.com/chat-agent-qa-screenshot)

## Frontend Code

### Overview

The frontend code is responsible for the user interface and user interactions. It is built using [insert technologies used, e.g., React, Vue.js, etc.]. The main files in the frontend directory include:

- `frontend.py`: This file contains the main logic for rendering the UI and handling user inputs.

### How to Run the Frontend Code

To run the frontend code, execute the following command in your terminal:

```bash
python frontend.py
```

This will start the frontend server, and you can access the application at `http://localhost:8000`.

## Backend Code

### Overview

The backend code handles data processing, business logic, and communication with the database. The main files in the backend directory include:

- `backend.py`: This file contains the API endpoints and the logic for handling requests and responses.

### How to Run the Backend Code

To run the backend code, execute the following command in your terminal:

```bash
python backend.py
```

This will start the backend server, and it will listen for incoming requests.

## AI Code (data.py)

### Overview

The `data.py` file contains the AI logic that processes data and performs analysis. It includes functions for [insert specific functionalities, e.g., data cleaning, model training, etc.].

### How to Use the AI Code

To use the AI code, you can import the functions from `data.py` in your scripts or run it directly:

```bash
python data.py
```

This will execute the AI processes defined in the file.
