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

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="Student Assessment Dashboard", layout="wide")
st.title("🏫 Student Assessment Dashboard")

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

# ---------------- STUDENT DROPDOWN ----------------
students = sorted(df["Roll"].unique().tolist())
selected_student = st.selectbox("Select Student Roll Number", students)

student_df = df[df["Roll"] == selected_student]

if student_df.empty:
    st.info("No data for selected student.")
    st.stop()

# ---------------- SUMMARY (no raw questions) ----------------
st.markdown("### 🧾 Student Summary")

sections = student_df["Section"].unique()
summary_records = []

for sec in sections:
    subset = student_df[student_df["Section"] == sec]
    likert_df = subset[subset["Type"].isin(["likert", "mcq"])].copy()
    likert_df["Numeric"] = pd.to_numeric(likert_df["Response"], errors="coerce")
    avg_score = likert_df["Numeric"].mean(skipna=True)
    summary_records.append({"Section": sec, "LikertAvg": round(avg_score, 2)})

summary_df = pd.DataFrame(summary_records)
st.dataframe(summary_df, use_container_width=True)

# ---------------- SHORT ANSWER EVALUATION ----------------
short_df = student_df[student_df["Type"] == "short"].copy()

if not short_df.empty:
    st.markdown("### ✍️ Manual Evaluation for Short Answers")

    for idx, row in short_df.iterrows():
        st.markdown(f"**Q{row['QuestionID']}: {row['Question']}**")
        st.info(f"**Student Answer:** {row['Response']}")
        mark = st.number_input(
            f"Marks (1 mark max) for Q{row['QuestionID']}",
            min_value=0.0, max_value=1.0, step=0.5,
            key=f"mark_{selected_student}_{idx}"
        )

        if st.button(f"💾 Save Marks for {row['QuestionID']}", key=f"save_{idx}"):
            doc_id = f"{row['Roll']}_{row['Section'].replace(' ', '_')}_{row['QuestionID']}"
            record = {
                "Roll": row["Roll"],
                "Section": row["Section"],
                "QuestionID": row["QuestionID"],
                "AnswerText": row["Response"],
                "Marks": mark,
                "Evaluator": "Faculty",
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            db.collection("short_marks").document(doc_id).set(record)
            st.success(f"Saved marks for {row['QuestionID']} ✅")

else:
    st.info("No short-answer questions for this student.")

# ---------------- TOTAL MARKS (from likert + short) ----------------
marks_docs = db.collection("short_marks").stream()
marks_data = [d.to_dict() for d in marks_docs if d.to_dict().get("Roll") == selected_student]
marks_df = pd.DataFrame(marks_data)

if not marks_df.empty:
    short_total = marks_df["Marks"].sum()
else:
    short_total = 0

numeric_df = student_df.copy()
numeric_df["Numeric"] = pd.to_numeric(numeric_df["Response"], errors="coerce")
likert_total = numeric_df["Numeric"].sum(skipna=True)
grand_total = likert_total + short_total

st.markdown("---")
st.metric(label="🏅 Total Marks (All Sections Combined)", value=f"{grand_total:.2f}")
st.markdown("---")

# ---------------- BACK TO TOP BUTTON ----------------
st.markdown("""
    <style>
    #back-to-top {
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
    </style>
    <button id="back-to-top" onclick="window.scrollTo({top: 0, behavior: 'smooth'})">
        ⬆ Back to Top
    </button>
""", unsafe_allow_html=True)
