import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import json

# -------------------------------------------------------------
# 🔹 Firebase Setup
# -------------------------------------------------------------
if not firebase_admin._apps:
    try:
        firebase_config = json.loads(st.secrets["firebase_key"])
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}")

# -------------------------------------------------------------
# 🔹 File Mapping
# -------------------------------------------------------------
files = {
    "Aptitude Test": "aptitude.csv",
    "Adaptability & Learning": "adaptability_learning.csv",
    "Communication Skills - Objective": "communcation_skills_objective.csv",
    "Communication Skills - Descriptive": "communcation_skills_descriptive.csv"
}

# -------------------------------------------------------------
# 🔹 Streamlit UI
# -------------------------------------------------------------
st.set_page_config(page_title="Assessment Portal", layout="wide")
st.title("🎓 Student Assessment Portal")

name = st.text_input("Enter Your Name")
roll = st.text_input("Enter Roll Number (e.g., 24bbab110)")

if name and roll:
    st.success(f"Welcome, {name}! Please choose a section to begin.")
    section = st.selectbox("Select Section", list(files.keys()))

    if section:
        try:
            df = pd.read_csv(files[section])
        except FileNotFoundError:
            st.error(f"❌ File not found for section: {section}")
        else:
            st.markdown("---")
            st.subheader(f"📘 {section}")

            responses = {}
            score = 0

            for idx, row in df.iterrows():
                q = row["Question"]
                st.markdown(f"**Q{idx+1}. {q}**")

                # ---------------------------------------------------------
                # APTITUDE + COMMUNICATION OBJECTIVE (MCQ)
                # ---------------------------------------------------------
                if "A" in df.columns and not pd.isna(row.get("A", "")):
                    options = [row["A"], row["B"], row["C"], row["D"]]
                    answer = st.radio(f"Your answer for Q{idx+1}", options, key=f"q{idx}")
                    responses[q] = answer

                    correct = str(row.get("Correct", "")).strip()
                    if correct and answer == correct:
                        score += 1

                # ---------------------------------------------------------
                # ADAPTABILITY (LIKERT SCALE)
                # ---------------------------------------------------------
                elif "Likert" in df.columns or "Scale" in section:
                    rating = st.radio(
                        "Your response:",
                        ["1 – Strongly Disagree", "2 – Disagree", "3 – Neutral", "4 – Agree", "5 – Strongly Agree"],
                        key=f"l{idx}",
                    )
                    responses[q] = rating

                # ---------------------------------------------------------
                # DESCRIPTIVE QUESTIONS
                # ---------------------------------------------------------
                else:
                    text = st.text_area(f"Your Answer for Q{idx+1}", key=f"t{idx}")
                    responses[q] = text

            # -------------------------------------------------------------
            # 🔹 Submit Button
            # -------------------------------------------------------------
            if st.button("✅ Submit Responses"):
                try:
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
