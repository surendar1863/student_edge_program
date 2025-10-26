import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import json
import time
from datetime import datetime

# ---------------- FIREBASE INIT ----------------
try:
    # Get the config from Streamlit secrets
    firebase_config = st.secrets["firebase_key"]
    
    # If it's stored as a string, parse it to dict
    if isinstance(firebase_config, str):
        firebase_config = json.loads(firebase_config)
    
    # Create credentials
    cred = credentials.Certificate(firebase_config)
    
    # Initialize Firebase
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    
    # Get Firestore client
    db = firestore.client()
    
except Exception as e:
    st.error(f"❌ Firebase connection failed: {e}")
    st.stop()

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
roll = st.text_input("Enter Roll Number (e.g., 25BBAB170)")

# ---------------- MAIN APP ----------------
if name and roll:
    st.success(f"Welcome, {name}! Please choose a test section below.")
    section = st.selectbox("Select Section", list(files.keys()))

    if section:
        try:
            df = pd.read_csv(files[section])
        except FileNotFoundError:
            st.error(f"❌ Could not find {files[section]}. Please make sure the CSV file exists.")
            st.stop()
            
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
                    key=f"q{idx}_{roll}_{section}"
                )

            # MCQ
            elif qtype == "mcq":
                options = [
                    str(row.get(f"Option{i}", "")).strip()
                    for i in range(1, 5)
                    if pd.notna(row.get(f"Option{i}")) and str(row.get(f"Option{i}")).strip() != ""
                ]
                if options:
                    response = st.radio("Your Answer:", options, key=f"q{idx}_{roll}_{section}")
                else:
                    st.warning(f"No options available for {qid}")
                    response = ""

            # Short / Descriptive
            elif qtype == "short":
                response = st.text_area("Your Answer:", key=f"q{idx}_{roll}_{section}")

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
                
                try:
                    # ✅ FIXED LINE: Correct document ID creation
                    doc_ref = db.collection("student_responses").document(f"{roll}_{section.replace(' ', '_')}")
                    doc_ref.set(data)
                    
                    st.success("✅ Your responses have been successfully submitted!")
                    st.balloons()
                    
                    # Show preview
                    st.subheader("📋 Your Submitted Responses")
                    preview_data = []
                    for resp in responses:
                        preview_data.append({
                            "Question ID": resp["QuestionID"],
                            "Question": resp["Question"][:50] + "..." if len(resp["Question"]) > 50 else resp["Question"],
                            "Your Answer": str(resp["Response"])[:50] + "..." if len(str(resp["Response"])) > 50 else str(resp["Response"]),
                            "Type": resp["Type"]
                        })
                    
                    preview_df = pd.DataFrame(preview_data)
                    st.dataframe(preview_df, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ Error saving to database: {e}")

else:
    st.info("👆 Please enter your Name and Roll Number to start.")

# ---------------- SIMPLE EXPORT TO CSV ----------------
st.markdown("---")
st.header("📊 Export All Data to CSV")

if st.button("📥 Download All Responses as CSV"):
    try:
        # Get all data from Firestore
        docs = db.collection("student_responses").stream()
        
        all_data = []
        for doc in docs:
            doc_data = doc.to_dict()
            for response in doc_data.get("Responses", []):
                all_data.append({
                    "Timestamp": doc_data.get("Timestamp"),
                    "Name": doc_data.get("Name"),
                    "Roll": doc_data.get("Roll"),
                    "Section": doc_data.get("Section"),
                    "QuestionID": response.get("QuestionID"),
                    "Question": response.get("Question"),
                    "Response": response.get("Response"),
                    "Type": response.get("Type"),
                })
        
        if all_data:
            df = pd.DataFrame(all_data)
            
            # Create CSV
            csv_data = df.to_csv(index=False)
            
            # Download button
            st.download_button(
                label="📥 Download CSV File",
                data=csv_data,
                file_name=f"all_student_responses_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
            
            st.success(f"✅ Generated data for {len(all_data)} responses from {df['Roll'].nunique()} students")
            
            # Show preview
            st.subheader("📋 Data Preview")
            st.dataframe(df.head(10), use_container_width=True)
            
        else:
            st.warning("No student responses found yet.")
            
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
