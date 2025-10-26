import streamlit as st
import pandas as pd
import json
import time
import gspread
from google.oauth2.service_account import Credentials

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Student Edge Assessment", layout="wide")
st.title("🧠 Student Edge Assessment Portal")

# ---------------- GOOGLE SHEETS AUTH ----------------
# 🔸 If running locally, keep your service account file (e.g., service_account.json) in same folder.
# 🔸 If running on Streamlit Cloud, paste its content into "Secrets" under [google_service_account].

# ✅ Load service account from Streamlit Secrets
try:
    service_account_info = st.secrets["google_service_account"]
except Exception:
    # Fallback for local testing
    with open("service_account.json") as f:
        service_account_info = json.load(f)

# ✅ Create authorized gspread client
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
gc = gspread.authorize(credentials)

# ---------------- CONNECT TO GOOGLE SHEET ----------------
# 🔹 Create a Google Sheet named “Student_Responses”
# 🔹 Share it with your service account email (shown inside your JSON file)
SHEET_NAME = "Student_Responses"
try:
    sheet = gc.open(SHEET_NAME)
except gspread.SpreadsheetNotFound:
    st.error(f"❌ Google Sheet '{SHEET_NAME}' not found. Please create it and share with your service account.")
    st.stop()

# ---------------- CSV FILES ----------------
files = {
    "Aptitude Test": "aptitude.csv",
    "Adaptability & Learning": "adaptability_learning.csv",
    "Communication Skills - Objective": "communcation_skills_objective.csv",
    "Communication Skills - Descriptive": "communcation_skills_descriptive.csv",
}

# ---------------- STUDENT DETAILS ----------------
name = st.text_input("Enter Your Name")
roll = st.text_input("Enter Roll Number (e.g., 25BBAB170)")

if name and roll:
    st.success(f"Welcome, {name}! Please choose a test section below.")
    section = st.selectbox("Select Section", list(files.keys()))

    if section:
        df = pd.read_csv(files[section])
        st.subheader(f"📘 {section}")
        st.write("Answer all the questions below and click **Submit**.")

        responses = []
        for idx, row in df.iterrows():
            qid = row.get("QuestionID", f"Q{idx+1}")
            qtext = str(row.get("Question", "")).strip()
            qtype = str(row.get("Type", "")).strip().lower()

            if qtype == "info":
                st.markdown(f"### 📘 {qtext}")
                st.markdown("---")
                continue

            st.markdown(f"**Q{idx+1}. {qtext}**")

            if qtype == "likert":
                scale_min = int(row.get("ScaleMin", 1))
                scale_max = int(row.get("ScaleMax", 5))
                response = st.slider("Your Response:", min_value=scale_min,
                                     max_value=scale_max, value=(scale_min + scale_max)//2, key=f"q{idx}")

            elif qtype == "mcq":
                options = [str(row.get(f"Option{i}", "")).strip()
                           for i in range(1, 5)
                           if pd.notna(row.get(f"Option{i}")) and str(row.get(f"Option{i}")).strip() != ""]
                response = st.radio("Your Answer:", options, key=f"q{idx}") if options else ""

            elif qtype == "short":
                response = st.text_area("Your Answer:", key=f"q{idx}")

            else:
                response = ""
                st.warning(f"⚠️ Unknown question type '{qtype}'")

            responses.append({
                "QuestionID": qid,
                "Question": qtext,
                "Response": response,
                "Type": qtype,
            })
            st.markdown("---")

        # ---------------- SUBMIT ----------------
        if st.button("✅ Submit"):
            with st.spinner("Saving your responses to Google Sheets..."):
                # Prepare data
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                worksheet_title = section.replace(" ", "_")

                # Get or create a worksheet for this section
                try:
                    worksheet = sheet.worksheet(worksheet_title)
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = sheet.add_worksheet(title=worksheet_title, rows=1000, cols=20)
                    worksheet.append_row(["Timestamp", "Name", "Roll", "Section", "QuestionID", "Question", "Response", "Type"])

                # Append responses
                for r in responses:
                    row_data = [
                        timestamp,
                        name,
                        roll,
                        section,
                        r["QuestionID"],
                        r["Question"],
                        str(r["Response"]),
                        r["Type"]
                    ]
                    worksheet.append_row(row_data)

                st.success("✅ Responses saved successfully")
else:
    st.info("👆 Please enter your Name and Roll Number to start.")

