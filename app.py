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

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FOLDER = "pdfs"

# ---------------- DB INIT ----------------
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            birthdate TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.get("/")
def home():
    return FileResponse("Test UI.html")

# ---------------- REGISTER ----------------
@app.post("/register")
async def register(request: Request):
    data = await request.json()

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO users (first_name, last_name, birthdate, email, password)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data["first_name"],
            data["last_name"],
            data["birthdate"],
            data["email"],
            data["password"]
        ))

        conn.commit()
        return {"status": "success", "message": "Account created"}
    except:
        return {"status": "failed", "message": "Email already exists"}
    finally:
        conn.close()

# ---------------- LOGIN ----------------
@app.post("/login")
async def login(request: Request):
    data = await request.json()

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("""
        SELECT * FROM users 
        WHERE email=? AND password=?
    """, (data["email"], data["password"]))

    user = c.fetchone()
    conn.close()

    if user:
        return {"status": "success"}
    return {"status": "failed"}

# ---------------- UPLOAD PDF ----------------
@app.post("/upload")
async def upload_pdf(files: List[UploadFile] = File(...)):

    if os.path.exists(FOLDER):
        shutil.rmtree(FOLDER)

    os.makedirs(FOLDER, exist_ok=True)

    for file in files:
        file_path = os.path.join(FOLDER, file.filename)
        content = await file.read()

        with open(file_path, "wb") as f:
            f.write(content)

    return {"message": "uploaded"}

# ---------------- GET OUTPUT ----------------
@app.get("/get-output")
def get_output():

    if not os.path.exists(FOLDER):
        return []

    results = []

    for file in os.listdir(FOLDER):
        if file.endswith(".pdf"):

            reader = PdfReader(os.path.join(FOLDER, file))
            text = ""

            for p in reader.pages:
                if p.extract_text():
                    text += p.extract_text()

            name = re.search(r"EMPLOYEE\s*NAME\s*:?\s*(.+)", text, re.IGNORECASE)
            net = re.search(r"NET\s*PAY\s+([\d,]+)", text, re.IGNORECASE)
            basic = re.search(r"BASIC\s+([\d,]+)", text, re.IGNORECASE)

            results.append({
                "file": file,
                "name": name.group(1).split("EMPLOYEE")[0].strip() if name else "N/A",
                "net_pay": net.group(1) if net else "N/A",
                "basic_salary": basic.group(1) if basic else "N/A"
            })

    return results