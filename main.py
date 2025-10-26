import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import json
import time

# ---------------- FIREBASE CONNECTION ----------------
try:
    firebase_config = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(firebase_config)
except Exception:
    cred = credentials.Certificate("firebase_key.json")

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

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Student Edge Assessment", layout="wide")
st.title("🧠 Student Edge Assessment Portal")

# ---------------- STUDENT DETAILS ----------------
name = st.text_input("Enter Your Name")
roll = st.text_input("Enter Roll Number (e.g., 24bbab110)")

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

            # Instructional info text
            if qtype == "info":
                st.markdown(f"### 📝 {qtext}")
                st.markdown("---")
                continue

            st.markdown(f"**Q{idx+1}. {qtext}**")

            # Likert scale
            if qtype == "likert":
                scale_min = int(row.get("ScaleMin", 1))
                scale_max = int(row.get("ScaleMax", 5))
                response = st.slider(
                    "Your Response:",
                    min_value=scale_min,
                    max_value=scale_max,
                    value=(scale_min + scale_max) // 2,
                    key=f"q{idx}"
                )

            # MCQ
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

            # Short / Descriptive
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
                db.collection("student_responses").document(
                    f"{roll}_{section.replace(' ', '_')}"
                ).set(data)

                st.success("✅ Your responses have been successfully submitted!")

else:
    st.info("👆 Please enter your Name and Roll Number to start.")

# ---------------- BACK TO TOP BUTTON ----------------
st.markdown("""
    <style>
    .back-to-top {
        position: fixed;
        bottom: 40px;
        right: 40px;
        background-color: #0066cc;
        color: white;
        border: none;
        padding: 12px 18px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        transition: background-color 0.3s ease;
        z-index: 9999;
    }
    .back-to-top:hover {
        background-color: #004a99;
    }
    </style>
    <button class="back-to-top" onclick="window.scrollTo({top: 0, behavior: 'smooth'});">
        ⬆️ Back to Top
    </button>
    <script>
    window.addEventListener('scroll', function() {
        const button = document.querySelector('.back-to-top');
        if (window.scrollY > 200) {
            button.style.display = 'block';
        } else {
            button.style.display = 'none';
        }
    });
    </script>
""", unsafe_allow_html=True)


