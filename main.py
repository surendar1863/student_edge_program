import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# --- FIREBASE SETUP ---
cred = credentials.Certificate("firebase_key.json")
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- LOAD CSV FILES ---
files = {
    "Aptitude Test": "aptitude.csv",
    "Adaptability & Learning": "adaptability_learning.csv",
    "Communication Skills (Objective)": "communcation_skills_objective.csv",
    "Communication Skills (Descriptive)": "communcation_skills_descriptive.csv"
}

# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="Student Aptitude Assessment", layout="centered")

st.title("🧠 Aptitude & Skills Assessment System")
st.markdown("#### Garden City University - Department of Computer Science")
st.divider()

# --- STUDENT LOGIN ---
name = st.text_input("Enter Your Name")
roll = st.text_input("Enter Roll Number (e.g., 24bbab110)")

if name and roll:
    st.success(f"Welcome, {name}! Please choose a test section below.")
    st.divider()

    # --- SECTION SELECTION ---
    section = st.selectbox("Select Section", list(files.keys()))

    if section:
        df = pd.read_csv(files[section])

        if "Aptitude" in section or "Objective" in section:
            st.write(f"### {section} — MCQ Section")
            score = 0
            responses = {}

            for i, row in df.iterrows():
                st.markdown(f"**{row['No']}. {row['Question']}**")
                options = [row['A'], row['B'], row['C'], row['D']]
                ans = st.radio("", options, key=f"q_{i}")
                responses[row['No']] = ans
                if ans == row['Correct']:
                    score += 1
                st.divider()

            if st.button("Submit Section"):
                db.collection("responses").document(roll).set({
                    "Name": name,
                    "Roll": roll,
                    "Section": section,
                    "Score": score,
                    "Total": len(df),
                    "Answers": responses
                })
                st.success(f"✅ Section submitted! You scored {score} / {len(df)}")

        elif "Adaptability" in section:
            st.write("### Adaptability and Learning Questionnaire")
            st.markdown("Rate each statement from **1 (Strongly Disagree)** to **5 (Strongly Agree)**.")
            responses = {}

            for i, row in df.iterrows():
                rating = st.slider(row['Question'], 1, 5, 3, key=f"q_{i}")
                responses[row['No']] = rating

            if st.button("Submit Section"):
                db.collection("adaptability_scores").document(roll).set({
                    "Name": name,
                    "Roll": roll,
                    "Responses": responses
                })
                st.success("✅ Adaptability section submitted successfully!")

        elif "Descriptive" in section:
            st.write("### Communication Skills — Descriptive Answers")
            responses = {}
            for i, row in df.iterrows():
                ans = st.text_area(row['Question'], key=f"q_{i}")
                responses[row['No']] = ans

            if st.button("Submit Section"):
                db.collection("descriptive_responses").document(roll).set({
                    "Name": name,
                    "Roll": roll,
                    "Answers": responses
                })
                st.success("✅ Descriptive answers submitted successfully!")
else:
    st.warning("Please enter your name and roll number to begin.")
