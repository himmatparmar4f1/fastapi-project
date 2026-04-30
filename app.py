from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
from typing import List
import re
import os
import shutil

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FOLDER = "pdfs"


# 🌐 Serve HTML
@app.get("/")
def home():
    return FileResponse("Test UI.html")


# 📤 Upload (RESET old files + store new only)
@app.post("/upload")
async def upload_pdf(files: List[UploadFile] = File(...)):

    # 🔥 clear old files
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
        "message": "Old files removed, new files uploaded",
        "files": saved_files
    }


# 📊 Get Output (ONLY current uploaded files)
@app.get("/get-output")
def get_output():

    if not os.path.exists(FOLDER):
        return {"error": "No files uploaded yet"}

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

            # =========================
            # 🔥 EMPLOYEE NAME (FIXED)
            # =========================
            name_match = re.search(
                r"EMPLOYEE\s*NAME\s*:?\s*(.+)",
                full_text,
                re.IGNORECASE
            )

            if name_match:
                name = name_match.group(1).strip()
                name = name.split("EMPLOYEE CODE")[0].strip()
            else:
                name = "Not Found"

            # =========================
            # NET PAY
            # =========================
            net_pay_match = re.search(r"NET\s*PAY\s+([\d,]+)", full_text, re.IGNORECASE)
            net_pay = net_pay_match.group(1) if net_pay_match else "Not Found"

            # =========================
            # BASIC SALARY
            # =========================
            basic_match = re.search(r"BASIC\s+([\d,]+)", full_text, re.IGNORECASE)
            basic = basic_match.group(1) if basic_match else "Not Found"

            results.append({
                "file": file,
                "name": name,
                "net_pay": net_pay,
                "basic_salary": basic
            })

    return results