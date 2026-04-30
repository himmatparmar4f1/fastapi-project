from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
from typing import List
import sqlite3
import random
import string
import smtplib
from email.mime.text import MIMEText
import os
import shutil
import re

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FOLDER = "pdfs"

# ---------------- DB ----------------
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
        password TEXT,
        verified INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS otp_store (
        email TEXT,
        otp TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- EMAIL FUNCTION ----------------
def send_email(to_email, otp):

    sender_email = "yourgmail@gmail.com"
    app_password = "your_app_password"

    msg = MIMEText(f"Your verification code is: {otp}")
    msg["Subject"] = "OTP Verification Code"
    msg["From"] = sender_email
    msg["To"] = to_email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, app_password)
    server.sendmail(sender_email, to_email, msg.as_string())
    server.quit()

# ---------------- OTP GENERATOR ----------------
def generate_otp():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ---------------- HOME ----------------
@app.get("/")
def home():
    return FileResponse("Test UI.html")

# ---------------- SEND OTP ----------------
@app.post("/send-otp")
async def send_otp(request: Request):
    data = await request.json()
    email = data["email"]

    otp = generate_otp()

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("DELETE FROM otp_store WHERE email=?", (email,))
    c.execute("INSERT INTO otp_store VALUES (?,?)", (email, otp))

    conn.commit()
    conn.close()

    # REAL EMAIL SEND
    send_email(email, otp)

    return {"status": "sent"}

# ---------------- REGISTER ----------------
@app.post("/register")
async def register(request: Request):
    data = await request.json()

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("SELECT otp FROM otp_store WHERE email=?", (data["email"],))
    row = c.fetchone()

    if not row or row[0] != data["otp"]:
        return {"status": "failed", "message": "Invalid OTP"}

    c.execute("""
    INSERT INTO users (first_name,last_name,birthdate,email,password,verified)
    VALUES (?,?,?,?,?,1)
    """, (
        data["first_name"],
        data["last_name"],
        data["birthdate"],
        data["email"],
        data["password"]
    ))

    conn.commit()
    conn.close()

    return {"status": "success"}

# ---------------- LOGIN ----------------
@app.post("/login")
async def login(request: Request):
    data = await request.json()

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE email=? AND password=?",
              (data["email"], data["password"]))

    user = c.fetchone()
    conn.close()

    if user:
        return {
            "status": "success",
            "user": {
                "first_name": user[1],
                "last_name": user[2],
                "email": user[4]
            }
        }

    return {"status": "failed"}

# ---------------- UPDATE PASSWORD ----------------
@app.post("/update-password")
async def update_password(request: Request):
    data = await request.json()

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("UPDATE users SET password=? WHERE email=?",
              (data["password"], data["email"]))

    conn.commit()
    conn.close()

    return {"status": "updated"}

# ---------------- UPLOAD ----------------
@app.post("/upload")
async def upload(files: List[UploadFile] = File(...)):

    if os.path.exists(FOLDER):
        shutil.rmtree(FOLDER)

    os.makedirs(FOLDER, exist_ok=True)

    for f in files:
        with open(os.path.join(FOLDER, f.filename), "wb") as out:
            out.write(await f.read())

    return {"status": "uploaded"}

# ---------------- OUTPUT ----------------
@app.get("/get-output")
def output():

    if not os.path.exists(FOLDER):
        return []

    res = []

    for f in os.listdir(FOLDER):
        if f.endswith(".pdf"):

            reader = PdfReader(os.path.join(FOLDER, f))
            text = ""

            for p in reader.pages:
                if p.extract_text():
                    text += p.extract_text()

            name = re.search(r"EMPLOYEE\s*NAME\s*:?\s*(.+)", text, re.I)
            net = re.search(r"NET\s*PAY\s+([\d,]+)", text, re.I)
            basic = re.search(r"BASIC\s+([\d,]+)", text, re.I)

            res.append({
                "file": f,
                "name": name.group(1) if name else "N/A",
                "net_pay": net.group(1) if net else "N/A",
                "basic_salary": basic.group(1) if basic else "N/A"
            })

    return res