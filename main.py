import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import json
import time

# ---------------- FIREBASE CONNECTION ----------------
# Load credentials from Streamlit secrets (on Streamlit Cloud) or local file
try:
    firebase_config = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(firebase_config)
except Exception:
    cred = credentials.Certificate("firebase_key.json")

# Initialize Firebase only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- CSV FILES ----------------
files = {
    "Aptitude Test": "aptitude.csv",
    "Adaptability & Learning": "adaptability_learning.csv",
    "Communication Skills - Objective": "communcation_skills_objective.csv",
    "Communication Skills - Descriptive": "communcation_skills_descriptive.csv",
}

# ---------------- APP TITLE ----------------
st.set_page_config(page_title="Student Edge Assessment", layout="wide")
st.title("🧠 Student Edge Assessment Portal")

# ---------------- STUDENT DETAILS ----------------
name = st.text_input("Enter Your Name")
roll = st.text_input("Enter Roll Number (e.g., 24bbab110)")

if name and roll:
    st.success(f"Welcome, {name}! Please choose a test section below.")
    section = st.selectbox("Select Section", list(files.keys()))
    
    if section:
        df = pd.read_csv(files[section])
        st.subheader(f"📘 {section}")
        st.write("Answer all the questions below and click **Submit**.")
        
        responses = []
        for idx, row in df.iterrows():
            qid = row["QuestionID"]
            qtext = row["Question"]
            qtype = str(row.get("Type", "")).strip().lower()
            
            st.markdown(f"**Q{idx+1}. {qtext}**")

            if qtype == "info":
                st.markdown(f"### 📝 {row['Question']}")
                continue
                
            # Render Likert scale
            if qtype == "likert":
                scale_min = int(row.get("ScaleMin", 1))
                scale_max = int(row.get("ScaleMax", 5))
                response = st.slider(
                    f"Your rating for Q{idx+1}", 
                    min_value=scale_min, 
                    max_value=scale_max, 
                    value=(scale_max + scale_min)//2,
                    key=f"q{idx}"
                )

            # Render Multiple Choice
            elif qtype == "mcq":
                options = [str(row.get(f"Option{i}")) for i in range(1, 5) if pd.notna(row.get(f"Option{i}"))]
                response = st.radio(f"Your Answer for Q{idx+1}", options, key=f"q{idx}")

            # Render Short/Descriptive answer
            elif qtype == "short":
                response = st.text_area(f"Your Answer for Q{idx+1}", key=f"q{idx}")

            else:
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
                db.collection("student_responses").document(roll + "_" + section.replace(" ", "_")).set(data)
                st.success("Your responses have been successfully submitted!")
else:
    st.info("👆 Please enter your Name and Roll Number to start.")

