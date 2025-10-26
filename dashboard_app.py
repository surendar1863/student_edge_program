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
            "ScaleMin": r.get("ScaleMin", ""),
            "ScaleMax": r.get("ScaleMax", "")
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

# ---------------- INLINE LAYOUT ----------------
st.markdown("""
<style>
.qrow {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #ddd;
    padding: 8px 6px;
}
.qtext {
    flex: 1;
    font-size: 15px;
    font-weight: 500;
    color: #111;
}
.qradio {
    flex-shrink: 0;
    margin-left: 20px;
}
</style>
""", unsafe_allow_html=True)

marks_state = {}

# Display all questions in one line with radio buttons
for idx, row in student_df.iterrows():
    qid = row["QuestionID"]
    qtext = row["Question"]
    qtype = row["Type"]
    prev_mark = int(row["Marks"]) if not pd.isna(row["Marks"]) else 0

    # Inline container
    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown(f"**Q{idx+1}:** {qtext}")
    with col2:
        marks_state[qid] = st.radio(
            label="",
            options=[0, 1],
            index=prev_mark,
            horizontal=True,
            key=f"{selected_student}_{qid}"  # unique key per student-question
        )

# ---------------- SAVE ALL BUTTON ----------------
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

# ---------------- TOTAL ----------------
marks_docs = db.collection("faculty_marks").stream()
marks_data = [d.to_dict() for d in marks_docs if d.to_dict().get("Roll") == selected_student]
marks_df = pd.DataFrame(marks_data)
total_marks = marks_df["Marks"].sum() if not marks_df.empty else 0
max_marks = len(student_df)

st.metric(label="🏅 Total Marks (All Questions)", value=f"{total_marks}/{max_marks}")

# ---------------- BACK TO TOP ----------------
st.markdown("""
<style>
.back-to-top {
    position: fixed;
    bottom: 40px;
    right: 40px;
    background-color: #007bff;
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    z-index: 9999;
}
.back-to-top:hover { background-color: #0056b3; }
</style>
<button class="back-to-top" onclick="window.scrollTo({top:0,behavior:'smooth'})">⬆ Back to Top</button>
""", unsafe_allow_html=True)
