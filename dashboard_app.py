import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import json

# ---------------- FIREBASE INIT ----------------
try:
    firebase_key = dict(st.secrets["google_service_account"])
    cred = credentials.Certificate(firebase_key)
except Exception as e:
    st.error(f"Firebase config error: {e}")
    st.stop()

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="📊 Student Assessment Dashboard", layout="wide")
st.title("📊 Student Assessment Dashboard")

# ---------------- FETCH DATA ----------------
def fetch_all_responses():
    responses = []
    docs = db.collection("student_responses").stream()
    for doc in docs:
        data = doc.to_dict()
        for res in data["Responses"]:
            responses.append({
                "Timestamp": data["Timestamp"],
                "Name": data["Name"],
                "Roll": data["Roll"],
                "Section": data["Section"],
                "QuestionID": res["QuestionID"],
                "Question": res["Question"],
                "Response": res["Response"],
                "Type": res["Type"]
            })
    return pd.DataFrame(responses)

# ---------------- DISPLAY ----------------
if st.button("🔄 Load Responses"):
    df = fetch_all_responses()
    if df.empty:
        st.warning("No responses found yet.")
    else:
        st.success(f"Loaded {len(df)} responses.")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download as CSV", csv, "student_responses.csv", "text/csv")
