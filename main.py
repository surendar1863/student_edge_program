import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import gspread
import json
import time

# --------------------------------------------------------------------
# 🔹 FIREBASE + GOOGLE SHEETS INITIALIZATION
# --------------------------------------------------------------------
try:
    firebase_key = dict(st.secrets["google_service_account"])
    cred = credentials.Certificate(firebase_key)
except Exception as e:
    st.warning(f"⚠️ Streamlit secrets not found: {e}")
    cred = credentials.Certificate("firebase_key.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

@st.cache_resource
def get_google_sheet():
    try:
        gc = gspread.service_account_from_dict(st.secrets["google_service_account"])
        return gc.open("Student_Responses")
    except Exception as e:
        st.error(f"Google Sheets access error: {e}")
        return None


# --------------------------------------------------------------------
# 🔹 PAGE SETTINGS
# --------------------------------------------------------------------
st.set_page_config(page_title="Student Edge Assessment Portal", layout="wide")
st.title("🧠 Student Edge Assessment Portal")

# --------------------------------------------------------------------
# 🔹 LOAD CSV SECTIONS
# --------------------------------------------------------------------
files = {
    "Aptitude Test": "aptitude.csv",
    "Adaptability & Learning": "adaptability_learning.csv",
    "Communication Skills - Objective": "communcation_skills_objective.csv",
    "Communication Skills - Descriptive": "communcation_skills_descriptive.csv",
}

# --------------------------------------------------------------------
# 🔹 SAVE FUNCTIONS
# --------------------------------------------------------------------
def save_to_firestore(data):
    """Save student responses to Firebase Firestore"""
    try:
        doc_name = f"{data['Roll']}_{data['Section'].replace(' ', '_')}"
        db.collection("student_responses").document(doc_name).set(data)
        return True
    except Exception as e:
        st.error(f"Firestore save error: {e}")
        return False


def save_to_google_sheets(data):
    """Save student responses to Google Sheet"""
    try:
        sheet = get_google_sheet()
        if not sheet:
            return False

        try:
            ws = sheet.worksheet(data["Section"])
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title=data["Section"], rows=1000, cols=20)
            ws.append_row(["Timestamp", "Name", "Roll", "Section", "QuestionID", "Question", "Response", "Type"])

        for resp in data["Responses"]:
            ws.append_row([
                data["Timestamp"], data["Name"], data["Roll"], data["Section"],
                resp["QuestionID"], resp["Question"], str(resp["Response"]), resp["Type"]
            ])
        return True
    except Exception as e:
        st.error(f"Google Sheets error: {e}")
        return False


# --------------------------------------------------------------------
# 🔹 STUDENT INPUT
# --------------------------------------------------------------------
name = st.text_input("Enter Your Name")
roll = st.text_input("Enter Roll Number (e.g., 25BBAB170)")

if name and roll:
    section = st.selectbox("Select Section", list(files.keys()))
    if section:
        df = pd.read_csv(files[section])
        st.subheader(f"📘 {section}")
        responses = []

        for idx, row in df.iterrows():
            qid = row.get("QuestionID", f"Q{idx+1}")
            qtext = str(row.get("Question", "")).strip()
            qtype = str(row.get("Type", "")).strip().lower()

            if qtype == "info":
                st.markdown(f"### 📘 {qtext}")
                st.divider()
                continue

            st.markdown(f"**Q{idx+1}. {qtext}**")

            if qtype == "likert":
                response = st.slider("Your Response", 1, 5, 3, key=f"{qid}")
            elif qtype == "mcq":
                options = [str(row.get(f"Option{i}", "")).strip() for i in range(1, 5) if pd.notna(row.get(f"Option{i}"))]
                response = st.radio("Your Answer", options, key=f"{qid}")
            elif qtype == "short":
                response = st.text_area("Your Answer", key=f"{qid}")
            else:
                response = ""

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
                f_ok = save_to_firestore(data)
                s_ok = save_to_google_sheets(data)

                if f_ok and s_ok:
                    st.success("✅ Responses saved to Firestore and Google Sheets successfully!")
                elif f_ok:
                    st.warning("⚠️ Saved only to Firestore. Google Sheets upload failed.")
                else:
                    st.error("❌ Failed to save data. Please retry.")
else:
    st.info("👆 Please enter your Name and Roll Number to start.")
