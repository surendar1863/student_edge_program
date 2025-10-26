import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import json
from datetime import datetime

# ---------------- FIREBASE INIT ----------------
try:
    firebase_config = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(firebase_config)
except Exception:
    cred = credentials.Certificate("firebase_key.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Faculty Evaluation Dashboard", layout="wide")
st.title("🎓 Faculty Evaluation Dashboard")

# ---------------- LOAD STUDENT RESPONSES ----------------
collection_ref = db.collection("student_responses")
docs = list(collection_ref.stream())
if not docs:
    st.warning("No student data found in Firestore.")
    st.stop()

data = []
for doc in docs:
    d = doc.to_dict()
    for r in d.get("Responses", []):
        # Only include gradable (non-info) questions
        if r.get("Type") != "info":
            data.append({
                "Name": d.get("Name"),
                "Roll": d.get("Roll"),
                "Section": d.get("Section"),
                "QuestionID": r.get("QuestionID"),
                "Question": r.get("Question"),
                "Response": r.get("Response"),
                "Type": r.get("Type"),
            })
df = pd.DataFrame(data)

# ---------------- STUDENT SELECTION ----------------
students = sorted(df["Roll"].unique().tolist())
selected_student = st.selectbox("Select Student Roll Number", students)

student_df = df[df["Roll"] == selected_student]
if student_df.empty:
    st.info("No data found for this student.")
    st.stop()

st.subheader(f"📋 Evaluation for {student_df.iloc[0]['Name']} ({selected_student})")

# ---------------- LOAD EXISTING MARKS ----------------
mark_docs = db.collection("faculty_marks").stream()
mark_data = [d.to_dict() for d in mark_docs if d.to_dict().get("Roll") == selected_student]
marks_df = pd.DataFrame(mark_data) if mark_data else pd.DataFrame(columns=["QuestionID", "Marks"])
student_df = student_df.merge(marks_df, on="QuestionID", how="left")

# ---------------- STYLING ----------------
st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] { margin-bottom: -6px !important; }
div[class*="stRadio"] { margin-top: -8px !important; margin-bottom: -8px !important; }
.block-container { padding-top: 1rem; padding-bottom: 1rem; }

.qtext { font-size:16px; font-weight:600; color:#111; margin-bottom:3px; }
.qresp { font-size:15px; color:#333; margin-top:-4px; margin-bottom:4px; }

.infoblock { 
    background-color:#f0f8ff; 
    padding:16px 20px; 
    border-left:5px solid #007bff;
    border-radius:10px; 
    margin:18px 0 20px 0; 
    font-size:16px; 
    line-height:1.6;
    color:#222;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

.info-title {
    font-size:18px; 
    font-weight:700; 
    color:#007bff; 
    margin-bottom:10px;
    display: block;
}

.back-to-top {
    position: fixed; bottom: 40px; right: 40px;
    background-color: #007bff; color: white;
    border: none; padding: 10px 16px;
    border-radius: 8px; font-weight: 600;
    cursor: pointer; box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    z-index: 9999;
}
.back-to-top:hover { background-color: #0056b3; }
</style>
""", unsafe_allow_html=True)

# ---------------- MARK ENTRY SECTION ----------------
marks_state = {}
sections = student_df["Section"].unique().tolist()
grand_total = 0
grand_max = 0

# Define CSVs per section
section_files = {
    "Aptitude Test": "aptitude.csv",
    "Adaptability & Learning": "adaptability_learning.csv", 
    "Communication Skills - Objective": "communcation_skills_objective.csv",
    "Communication Skills - Descriptive": "communcation_skills_descriptive.csv",
}

for section in sections:
    sec_df = student_df[student_df["Section"] == section]
    st.markdown(f"## 🧾 {section}")
    
    # ✅ Display Reading Passages for this section (info type only)
    if section in section_files:
        try:
            section_csv = pd.read_csv(section_files[section])
            info_content = section_csv[section_csv["Type"] == "info"]
            for _, row in info_content.iterrows():
                qtext = row["Question"]
                st.markdown(
                    f"""
                    <div class='infoblock'>
                        <span class='info-title'>📘 Read the passage and answer the questions below:</span>
                        {qtext}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        except Exception as e:
            st.warning(f"⚠️ Could not load info content for {section}: {e}")

    # ✅ Display gradable questions
    section_total = 0
    section_max_marks = len(sec_df)
    question_counter = 0

    for _, row in sec_df.iterrows():
        qid = row["QuestionID"]
        qtext = row["Question"]
        response = str(row["Response"]) if pd.notna(row["Response"]) else "(No response)"
        prev_mark = int(row["Marks"]) if not pd.isna(row["Marks"]) else 0

        question_counter += 1
        
        col1, col2 = st.columns([10, 2])
        with col1:
            st.markdown(
                f"""
                <div class='qtext'>Q{question_counter}: {qtext}</div>
                <div class='qresp'>🧩 <i>Student Response:</i> <b>{response}</b></div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            marks_state[qid] = st.radio(
                label="",
                options=[0, 1],
                index=prev_mark,
                horizontal=True,
                key=f"{selected_student}_{section}_{qid}"
            )
            section_total += marks_state[qid]

    st.markdown(f"**Subtotal for {section}: {section_total}/{section_max_marks}**")
    st.markdown("---")

    grand_total += section_total
    grand_max += section_max_marks

# ---------------- SAVE BUTTON ----------------
if st.button("💾 Save All Marks"):
    for qid, mark in marks_state.items():
        db.collection("faculty_marks").document(f"{selected_student}_{qid}").set({
            "Roll": selected_student,
            "QuestionID": qid,
            "Marks": int(mark),
            "Evaluator": "Faculty",
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    st.success("✅ All marks saved successfully!")

# ---------------- TOTAL MARKS ----------------
st.metric(label="🏅 Total Marks (All Sections)", value=f"{grand_total}/{grand_max}")

# ---------------- BACK TO TOP ----------------
st.markdown("""
<a href="#top" class="back-to-top">⬆ Back to Top</a>
""", unsafe_allow_html=True)
