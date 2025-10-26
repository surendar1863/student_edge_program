import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import json
from datetime import datetime

# --------------------------------------------------------------------
# 🔹 FIREBASE INIT
# --------------------------------------------------------------------
try:
    firebase_key = dict(st.secrets["google_service_account"])
    cred = credentials.Certificate(firebase_key)
except Exception:
    cred = credentials.Certificate("firebase_key.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --------------------------------------------------------------------
# 🔹 PAGE SETTINGS
# --------------------------------------------------------------------
st.set_page_config(page_title="Faculty Evaluation Dashboard", layout="wide")
st.title("🎓 Faculty Evaluation Dashboard")

# --------------------------------------------------------------------
# 🔹 LOAD STUDENT RESPONSES
# --------------------------------------------------------------------
docs = list(db.collection("student_responses").stream())
if not docs:
    st.warning("No student responses found.")
    st.stop()

data = []
for doc in docs:
    d = doc.to_dict()
    for r in d.get("Responses", []):
        if r.get("Type") in ["short", "descriptive", "likert"]:
            data.append({
                "Name": d["Name"],
                "Roll": d["Roll"],
                "Section": d["Section"],
                "QuestionID": r["QuestionID"],
                "Question": r["Question"],
                "Response": r["Response"],
                "Type": r["Type"]
            })

df = pd.DataFrame(data)
students = sorted(df["Roll"].unique().tolist())
selected = st.selectbox("Select Student Roll", students)

if selected:
    s_df = df[df["Roll"] == selected]
    st.subheader(f"📄 Evaluation for {s_df.iloc[0]['Name']} ({selected})")

    marks_state = {}
    total, max_marks = 0, len(s_df)

    for idx, row in s_df.iterrows():
        qid = row["QuestionID"]
        st.markdown(f"**{row['Question']}**")
        st.markdown(f"🧩 *Student Response:* {row['Response']}")
        marks_state[qid] = st.radio("Marks", [0, 1], horizontal=True, key=f"{selected}_{qid}")
        total += marks_state[qid]
        st.markdown("---")

    if st.button("💾 Save Marks"):
        for qid, mark in marks_state.items():
            db.collection("faculty_marks").document(f"{selected}_{qid}").set({
                "Roll": selected,
                "QuestionID": qid,
                "Marks": mark,
                "Evaluator": "Faculty",
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        st.success(f"✅ Marks saved for {selected}")

    st.metric(label="🏅 Total", value=f"{total}/{max_marks}")
