import os
 qazedc#@!12A
# Read output line by line

with os.popen("df -h") as f:

    for line in f.readlines():

        print(line.strip())
 
# Run a shell command and capture output

output = os.popen("uname -a").read()

print(output)
 
Got it — if you want to run the Playwright test suite (npm playwright) in the same pod as your FastAPI app, here's how you can do it safely and concurrently for multiple users:
✅ Key Requirements Recap:
Multiple users upload zipped Playwright test suites (JavaScript).
You unzip and run npm install && npx playwright test in each user's test suite.
Store HTML reports in user-specific folders under a static path.
Avoid users overwriting each other's files during concurrent execution.
✅ Approach for Shared Pod Execution
You’ll need to:
Use unique directories per request (e.g., with uuid or timestamp).
Run npm playwright in those isolated folders.
Ensure concurrent execution using asyncio or a ThreadPoolExecutor.
🧠 Directory Structure Example
/app/
  ├── uploads/
  │     └── user_abc123/
  │            ├── package.json
  │            └── tests/
  ├── reports/
        └── user_abc123/
               └── index.html
🚀 Code Sample
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import os
import uuid
import shutil
import subprocess
import asyncio
import zipfile
app = FastAPI()
BASE_UPLOAD_PATH = "/app/uploads"
BASE_REPORT_PATH = "/app/reports"
os.makedirs(BASE_UPLOAD_PATH, exist_ok=True)
os.makedirs(BASE_REPORT_PATH, exist_ok=True)

def unzip_to_dir(zip_file: UploadFile, extract_path: str):
    with zipfile.ZipFile(zip_file.file) as zip_ref:
        zip_ref.extractall(extract_path)

def run_playwright(project_path: str, report_path: str):
    env = os.environ.copy()
    env["PLAYWRIGHT_HTML_REPORT"] = report_path  # Set report path
    subprocess.run(
        ["npm", "install"],
        cwd=project_path,
        env=env,
        check=True
    )
    subprocess.run(
        ["npx", "playwright", "test", "--reporter=html"],
        cwd=project_path,
        env=env,
        check=True
    )

@app.post("/run/")
async def run_playwright_zip(zip_file: UploadFile = File(...)):
    # Create unique user path
    uid = uuid.uuid4().hex
    user_path = os.path.join(BASE_UPLOAD_PATH, uid)
    report_path = os.path.join(BASE_REPORT_PATH, uid)
    os.makedirs(user_path, exist_ok=True)
    os.makedirs(report_path, exist_ok=True)
    # Save and unzip
    zip_path = os.path.join(user_path, zip_file.filename)
    with open(zip_path, "wb") as f:
        f.write(await zip_file.read())
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(user_path)
    # Run playwright in executor (to allow concurrency)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_playwright, user_path, report_path)
    return JSONResponse({
        "status": "success",
        "report_url": f"/reports/{uid}/index.html"
    })

# Serve static reports
from fastapi.staticfiles import StaticFiles
app.mount("/reports", StaticFiles(directory=BASE_REPORT_PATH), name="reports")
# Serve static reports
from fastapi.staticfiles import StaticFiles
app.mount("/reports", StaticFiles(directory=BASE_REPORT_PATH), name="reports")
🔒 Security Note
Make sure the uploaded scripts:
Can’t access the rest of your pod filesystem.
Can’t hang the app (e.g., using timeouts or resource limits). If needed, run Playwright commands in a Docker sandbox via subprocess or restrict with ulimit.
✅ Benefits of This Approach
Simple: no extra containers or Jobs.
Fully concurrent (via asyncio.run_in_executor()).
One pod, isolated execution per request.
Would you like me to help add resource limits (e.g., max memory or execution time) for each test run?
 
Ankita Singh go through this and accordingly update your code
 
