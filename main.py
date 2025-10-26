import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import json

# ------------------------------------------------------------------
# 🔹 Firebase Initialization
# ------------------------------------------------------------------
if not firebase_admin._apps:
    try:
        firebase_config = json.loads(st.secrets["firebase_key"])
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}")

# ------------------------------------------------------------------
# 🔹 File Mapping
# ------------------------------------------------------------------
files = {
    "Aptitude Test": "aptitude.csv",
    "Adaptability & Learning": "adaptability_learning.csv",
    "Communication Skills - Objective": "communcation_skills_objective.csv",
    "Communication Skills - Descriptive": "communcation_skills_descriptive.csv"
}

# ------------------------------------------------------------------
# 🔹 Page Setup
# ------------------------------------------------------------------
st.set_page_config(page_title="Student Assessment Portal", layout="wide")
st.title("🎓 Student Assessment Portal")

# ------------------------------------------------------------------
# 🔹 Student Login
# ------------------------------------------------------------------
name = st.text_input("Enter Your Name")
roll = st.text_input("Enter Roll Number (e.g., 24bbab110)")

if name and roll:
    st.success(f"Welcome, {name}! Please choose a test section below.")

    # Select Section
    section = st.selectbox("Select Section", list(files.keys()))

    if section:
        try:
            df = pd.read_csv(files[section])
        except FileNotFoundError:
            st.error(f"❌ File not found for section: {section}")
        else:
            st.markdown("---")
            st.subheader(f"📘 {section}")
            st.markdown("Answer all the questions below and click **Submit**.")

            responses = {}
            score = 0

            # Identify column pattern based on question type
            for idx, row in df.iterrows():
                q = row["Question"]
                st.markdown(f"**Q{idx+1}. {q}**")

                # Objective Type
                if "A" in df.columns and not pd.isna(row.get("A", "")):
                    options = [row["A"], row["B"], row["C"], row["D"]]
                    answer = st.radio(f"Select your answer for Q{idx+1}", options, key=f"q{idx}")
                    responses[q] = answer

                    # Compare with Correct Answer (if present)
                    correct = str(row.get("Correct", "")).strip()
                    if correct and answer == correct:
                        score += 1

                # Descriptive Type
                else:
                    text = st.text_area(f"Your Answer for Q{idx+1}", key=f"t{idx}")
                    responses[q] = text

            # ------------------------------------------------------------------
            # 🔹 Submission and Firestore Storage
            # ------------------------------------------------------------------
            if st.button("✅ Submit Responses"):
                try:
                    # Prepare data for Firestore
                    doc_ref = db.collection("student_responses").document(roll)
                    doc_ref.set({
                        "Name": name,
                        "Roll": roll,
                        "Section": section,
                        "Score": int(score),
                        "Responses": responses
                    })
                    st.success(f"✅ Responses submitted successfully! Your Score")
                except Exception as e:
                    st.error(f"⚠️ Error saving data: {e}")

else:
    st.info("Please enter your Name and Roll Number to begin.")
