import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import json
import time
import gspread
from google.oauth2.service_account import json

# ---------------- FIREBASE CONNECTION ----------------
try:
    firebase_config = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(firebase_config)
except Exception:
    cred = credentials.Certificate("firebase_key.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------- GOOGLE SHEETS SETUP ----------------
@st.cache_resource
def get_google_sheet():
    try:
        # Use the same Firebase service account for Google Sheets
        gc = gspread.service_account_from_dict(st.secrets["firebase_key"])
        sheet = gc.open("Student_Responses")  # Your Google Sheet name
        return sheet
    except Exception as e:
        st.error(f"Google Sheets error: {e}")
        return None

# ---------------- CSV FILES ----------------
files = {
    "Aptitude Test": "aptitude.csv",
    "Adaptability & Learning": "adaptability_learning.csv",
    "Communication Skills - Objective": "communcation_skills_objective.csv",
    "Communication Skills - Descriptive": "communcation_skills_descriptive.csv",
}

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Student Edge Assessment", layout="wide")
st.title("🧠 Student Edge Assessment Portal")

# ---------------- FUNCTIONS ----------------
def save_to_google_sheets(data, roll_number, section):
    """Save responses to Google Sheets"""
    try:
        sheet = get_google_sheet()
        if not sheet:
            return False, "Could not access Google Sheet"
        
        # Get or create worksheet for this section
        try:
            worksheet = sheet.worksheet(section)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=section, rows=1000, cols=20)
            # Add headers
            headers = ["Timestamp", "Name", "Roll", "Section", "QuestionID", "Question", "Response", "Type"]
            worksheet.append_row(headers)
        
        # Append each response as a row
        for response in data["Responses"]:
            row = [
                data["Timestamp"],
                data["Name"],
                data["Roll"],
                data["Section"],
                response["QuestionID"],
                response["Question"],
                str(response["Response"]),
                response["Type"]
            ]
            worksheet.append_row(row)
        
        return True, f"Saved to sheet: {section}"
    except Exception as e:
        return False, str(e)

def save_to_firestore(data, roll_number, section):
    """Save responses to Firestore"""
    try:
        db.collection("student_responses").document(
            f"{roll_number}_{section.replace(' ', '_')}"
        ).set(data)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# ---------------- STUDENT DETAILS ----------------
name = st.text_input("Enter Your Name")
roll = st.text_input("Enter Roll Number (e.g., 25BBAB170)")

# ---------------- MAIN APP ----------------
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

            if qtype == "likert":
                scale_min = int(row.get("ScaleMin", 1))
                scale_max = int(row.get("ScaleMax", 5))
                response = st.slider(
                    "Your Response:", min_value=scale_min, max_value=scale_max,
                    value=(scale_min + scale_max) // 2, key=f"q{idx}"
                )

            elif qtype == "mcq":
                options = [
                    str(row.get(f"Option{i}", "")).strip()
                    for i in range(1, 5)
                    if pd.notna(row.get(f"Option{i}")) and str(row.get(f"Option{i}")).strip() != ""
                ]
                if options:
                    response = st.radio("Your Answer:", options, key=f"q{idx}")
                else:
                    st.warning(f"No options available for {qid}")
                    response = ""

            elif qtype == "short":
                response = st.text_area("Your Answer:", key=f"q{idx}")

            else:
                st.info(f"⚠️ Unknown question type '{qtype}' for {qid}.")
                response = ""

            responses.append({
                "QuestionID": qid,
                "Question": qtext,
                "Response": response,
                "Type": qtype,
            })
            st.markdown("---")

        # ---------------- SUBMIT ----------------
        if st.button("✅ Submit"):
            with st.spinner("Saving your responses..."):
                data = {
                    "Name": name,
                    "Roll": roll,
                    "Section": section,
                    "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Responses": responses,
                }
                
                # Save to both Firestore and Google Sheets
                success_firestore, firestore_msg = save_to_firestore(data, roll, section)
                success_sheets, sheets_msg = save_to_google_sheets(data, roll, section)
                
                if success_firestore and success_sheets:
                    st.success("""
                    ✅ Your responses have been successfully submitted!
                    
                    **Data saved to:**
                    - 📊 Firebase Firestore (for real-time access)
                    - 📊 Google Sheets (for Excel-like analysis)
                    """)
                else:
                    if success_firestore:
                        st.success("✅ Saved to Firestore, but Google Sheets failed")
                        st.warning(f"Sheets error: {sheets_msg}")
                    else:
                        st.error("❌ Failed to save responses. Please try again.")

else:
    st.info("👆 Please enter your Name and Roll Number to start.")
