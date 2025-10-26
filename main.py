import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import gspread
from google.oauth2.service_account import Credentials
import time
import json

# ---------------- FIREBASE + GOOGLE AUTH ----------------
try:
    firebase_key = dict(st.secrets["google_service_account"])
    cred = credentials.Certificate(firebase_key)
except Exception as e:
    st.error(f"Firebase config error: {e}")
    st.stop()

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------- GOOGLE SHEETS CONNECTION ----------------
@st.cache_resource
def get_google_sheet():
    try:
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        sheet = gc.open("Student_Responses")
        return sheet
    except Exception as e:
        st.error(f"Google Sheets error: {e}")
        return None

# ---------------- STREAMLIT PAGE ----------------
st.set_page_config(page_title="Student Edge Assessment Portal", layout="wide")
st.title("🧠 Student Edge Assessment Portal")

# ---------------- STUDENT DETAILS ----------------
name = st.text_input("Enter Your Name")
roll = st.text_input("Enter Roll Number (e.g., 25BBAB170)")

# ---------------- FILES ----------------
files = {
    "Aptitude Test": "aptitude.csv",
    "Adaptability & Learning": "adaptability_learning.csv",
    "Communication Skills - Objective": "communcation_skills_objective.csv",
    "Communication Skills - Descriptive": "communcation_skills_descriptive.csv",
}

def save_to_google_sheets(data, section):
    try:
        sheet = get_google_sheet()
        if not sheet:
            return False, "Sheet not found"

        try:
            worksheet = sheet.worksheet(section)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=section, rows=1000, cols=20)
            worksheet.append_row(["Timestamp", "Name", "Roll", "Section", "QuestionID", "Question", "Response", "Type"])

        for res in data["Responses"]:
            worksheet.append_row([
                data["Timestamp"],
                data["Name"],
                data["Roll"],
                data["Section"],
                res["QuestionID"],
                res["Question"],
                str(res["Response"]),
                res["Type"]
            ])
        return True, "Saved"
    except Exception as e:
        return False, str(e)

# ---------------- MAIN LOGIC ----------------
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
                st.markdown(f"### 📝 {qtext}")
                st.markdown("---")
                continue

            st.markdown(f"**Q{idx+1}. {qtext}**")

            if qtype == "mcq":
                options = [str(row.get(f"Option{i}", "")).strip()
                           for i in range(1, 5) if pd.notna(row.get(f"Option{i}"))]
                response = st.radio("Choose:", options, key=f"q{idx}")
            elif qtype == "likert":
                response = st.slider("Rate:", 1, 5, 3, key=f"q{idx}")
            else:
                response = st.text_area("Your Answer:", key=f"q{idx}")

            responses.append({
                "QuestionID": qid,
                "Question": qtext,
                "Response": response,
                "Type": qtype
            })
            st.markdown("---")

        if st.button("✅ Submit"):
            with st.spinner("Saving your responses..."):
                data = {
                    "Name": name,
                    "Roll": roll,
                    "Section": section,
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Responses": responses
                }
                # Save to Firestore and Sheets
                db.collection("student_responses").document(f"{roll}_{section.replace(' ', '_')}").set(data)
                success, msg = save_to_google_sheets(data, section)
                if success:
                    st.success("✅ Responses saved to Google Sheets and Firestore successfully!")
                else:
                    st.error(f"Error saving to Sheets: {msg}")
else:
    st.info("👆 Please enter your Name and Roll Number to start.")
