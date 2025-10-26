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

# ---------------- FILTER TYPES ----------------
# Keep likert, short, descriptive, and info; remove mcq
eval_df = student_df[student_df["Type"].isin(["likert", "short", "descriptive", "info"])].copy()
if eval_df.empty:
    st.info("No evaluable questions for this student.")
    st.stop()

# ---------------- LOAD EXISTING MARKS ----------------
mark_docs = db.collection("faculty_marks").stream()
mark_data = [d.to_dict() for d in mark_docs if d.to_dict().get("Roll") == selected_student]
marks_df = pd.DataFrame(mark_data) if mark_data else pd.DataFrame(columns=["QuestionID", "Marks"])
eval_df = eval_df.merge(marks_df, on="QuestionID", how="left")

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
    padding:15px 20px; 
    border-left:5px solid #007bff;
    border-radius:6px; 
    margin-bottom:20px; 
    font-size:16px; 
    line-height:1.6;
    color:#333;
    font-style: normal;
}
.info-title {
    font-size:18px; 
    font-weight:700; 
    color:#007bff; 
    margin-bottom:8px;
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
sections = eval_df["Section"].unique().tolist()
grand_total = 0
grand_max = 0

for section in sections:
    sec_df = eval_df[eval_df["Section"] == section]
    st.markdown(f"## 🧾 {section}")

    section_total = 0
    
    # Separate info content from gradable questions
    info_content = sec_df[sec_df["Type"] == "info"]
    gradable_questions = sec_df[sec_df["Type"] != "info"]
    
    section_max_marks = len(gradable_questions)
    
    # First display all info content - WITHOUT student responses
    for idx, row in info_content.iterrows():
        qtext = row["Question"]
        st.markdown(
            f"""
            <div class='infoblock'>
                <span class='info-title'>📘 Reading Passage</span>
                {qtext}
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    # Then display gradable questions with marks
    question_counter = 0
    for idx, row in gradable_questions.iterrows():
        qid = row["QuestionID"]
        qtext = row["Question"]
        qtype = row["Type"]
        response = str(row["Response"]) if pd.notna(row["Response"]) else "(No response)"
        prev_mark = int(row["Marks"]) if not pd.isna(row["Marks"]) else 0

        # Increment question counter
        question_counter += 1
        
        # Layout: Question + response + marks (0/1)
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
st.markdown("---")
st.markdown(
    '''
    <div style="text-align: center;">
        <a href="#" style="
            display: inline-block;
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            margin: 10px 0;
        ">⬆️ Back to Top</a>
    </div>
    ''', 
    unsafe_allow_html=True
)
