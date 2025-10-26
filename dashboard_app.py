import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import pandas as pd

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
# 🔹 Streamlit Dashboard UI
# -------------------------------------------------------------
st.set_page_config(page_title="Results Dashboard", layout="wide")
st.title("📊 Student Assessment Dashboard")

# Fetch data
docs = db.collection("student_responses").stream()
data = []

for doc in docs:
    d = doc.to_dict()
    data.append({
        "Name": d.get("Name", ""),
        "Roll": d.get("Roll", ""),
        "Section": d.get("Section", ""),
        "Score": d.get("Score", ""),
    })

if data:
    df = pd.DataFrame(data)
    st.dataframe(df)

    # Student Search
    st.subheader("🔍 Search by Student Roll Number")
    roll = st.text_input("Enter Roll Number")
    if roll:
        doc_ref = db.collection("student_responses").document(roll).get()
        if doc_ref.exists:
            st.json(doc_ref.to_dict())
        else:
            st.warning("No record found for this Roll Number.")

    # Section Analysis
    st.subheader("📈 Section-wise Statistics")
    avg_scores = df.groupby("Section")["Score"].mean().reset_index()
    st.bar_chart(avg_scores, x="Section", y="Score")

else:
    st.warning("No student responses found in Firestore.")
