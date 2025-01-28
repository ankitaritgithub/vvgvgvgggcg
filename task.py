from langchain_core.prompts import ChatPromptTemplate
import os
import csv
import requests

# Define the prompt template for generating CSV data
csv_gen_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a coding assistant with expertise in generating data. \n
            Your task is to generate a CSV file containing email and password fields for login data. \n
            Generate 10 rows of data with realistic email addresses and passwords. Provide the output as CSV data. \n
            The CSV file should have the following columns: email, password. Here is the user input:""",
        ),
        ("placeholder", "{messages}"),
    ]
)



api_key = os.getenv("api_key", "AIzaSyBmUrLDjqOzlrpVMUuYKxX00Mb_wdkq34Y")
model_name = os.getenv("LLM_MODEL", "gemini-1.5-flash")  
server_url = os.getenv("PROXY_SERVER_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-002:generateContent")

# Function to call the Gemini-1.5-Flash model
def generate_csv_with_gemini(prompt: str):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gemini-1.5-flash",
        "messages": [{"role": "system", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0,
    }
    response = requests.post(server_url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# Define the user prompt
user_message = """
Generate a CSV file containing 10 rows of login data. Each row should have:
- email (realistic, random email format)
- password (realistic, random password)
"""

# Generate the CSV data
prompt = csv_gen_prompt.format(messages=[("user", user_message)])
csv_data = generate_csv_with_gemini(prompt)

# Process and save the CSV data
output_dir = "testdata"
os.makedirs(output_dir, exist_ok=True)
file_path = os.path.join(output_dir, "testdata.csv")

# Write the CSV content to a file
with open(file_path, "w", newline="") as csv_file:
    csv_writer = csv.writer(csv_file)
    rows = csv_data.strip().split("\n")
    for row in rows:
        csv_writer.writerow(row.split(","))

print(f"CSV file generated and saved to {file_path}")
