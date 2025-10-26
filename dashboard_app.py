import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import json

# ---------------- FIREBASE CONNECTION ----------------
try:
    firebase_config = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(firebase_config)
except Exception:
    cred = credentials.Certificate("firebase_key.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------- DASHBOARD TITLE ----------------
st.set_page_config(page_title="Assessment Dashboard", layout="wide")
st.title("📊 Student Assessment Dashboard")

# ---------------- RETRIEVE DATA ----------------
collection_ref = db.collection("student_responses")
docs = collection_ref.stream()

data = []
for doc in docs:
    d = doc.to_dict()
    for r in d["Responses"]:
        data.append({
            "Name": d["Name"],
            "Roll": d["Roll"],
            "Section": d["Section"],
            "Timestamp": d["Timestamp"],
            "QuestionID": r["QuestionID"],
            "Question": r["Question"],
            "Response": r["Response"],
            "Type": r["Type"],
        })

if data:
    df = pd.DataFrame(data)
    st.success(f"Total Records Found: {len(df)}")
    section_list = df["Section"].unique().tolist()
    section = st.selectbox("Select Section", ["All"] + section_list)

    if section != "All":
        df = df[df["Section"] == section]

    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv,
        file_name="student_responses.csv",
        mime="text/csv"
    )
else:
    st.warning("No responses found in Firestore.")
