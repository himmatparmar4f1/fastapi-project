from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
from typing import List
import re
import os
import shutil
import sqlite3

app = FastAPI()

# ---------------------------
# CORS
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FOLDER = "pdfs"

# ---------------------------
# INIT DATABASE
# ---------------------------
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()


# ---------------------------
# SERVE UI
# ---------------------------
@app.get("/")
def home():
    return FileResponse("Test UI.html")


# ---------------------------
# REGISTER USER
# ---------------------------
@app.post("/register")
async def register(request: Request):
    data = await request.json()

    username = data["username"]
    password = data["password"]

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                  (username, password))
        conn.commit()
        return {"status": "success", "message": "User registered"}
    except:
        return {"status": "failed", "message": "User already exists"}
    finally:
        conn.close()


# ---------------------------
# LOGIN USER
# ---------------------------
@app.post("/login")
async def login(request: Request):
    data = await request.json()

    username = data["username"]
    password = data["password"]

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=? AND password=?", 
              (username, password))

    user = c.fetchone()
    conn.close()

    if user:
        return {"status": "success"}
    else:
        return {"status": "failed"}


# ---------------------------
# UPLOAD PDF
# ---------------------------
@app.post("/upload")
async def upload_pdf(files: List[UploadFile] = File(...)):

    if os.path.exists(FOLDER):
        shutil.rmtree(FOLDER)

    os.makedirs(FOLDER, exist_ok=True)

    saved_files = []

    for file in files:
        file_path = os.path.join(FOLDER, file.filename)

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        saved_files.append(file.filename)

    return {
        "message": "Files uploaded successfully",
        "files": saved_files
    }


# ---------------------------
# GET OUTPUT FROM PDF
# ---------------------------
@app.get("/get-output")
def get_output():

    if not os.path.exists(FOLDER):
        return []

    results = []

    for file in os.listdir(FOLDER):
        if file.endswith(".pdf"):
            file_path = os.path.join(FOLDER, file)

            reader = PdfReader(file_path)
            full_text = ""

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

            # EMPLOYEE NAME
            name_match = re.search(r"EMPLOYEE\s*NAME\s*:?\s*(.+)", full_text, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).split("EMPLOYEE CODE")[0].strip()
            else:
                name = "Not Found"

            # NET PAY
            net_pay_match = re.search(r"NET\s*PAY\s+([\d,]+)", full_text, re.IGNORECASE)
            net_pay = net_pay_match.group(1) if net_pay_match else "Not Found"

            # BASIC SALARY
            basic_match = re.search(r"BASIC\s+([\d,]+)", full_text, re.IGNORECASE)
            basic = basic_match.group(1) if basic_match else "Not Found"

            results.append({
                "file": file,
                "name": name,
                "net_pay": net_pay,
                "basic_salary": basic
            })

    return results