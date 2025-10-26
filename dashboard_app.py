import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import plotly.express as px
import json
from datetime import datetime

# ---------------- FIREBASE CONNECTION ----------------
try:
    firebase_config = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(firebase_config)
except Exception:
    cred = credentials.Certificate("firebase_key.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- PAGE SETUP ----------------
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
            "Name": d.get("Name", ""),
            "Roll": d.get("Roll", ""),
            "Section": d.get("Section", ""),
            "Timestamp": d.get("Timestamp", ""),
            "QuestionID": r.get("QuestionID", ""),
            "Question": r.get("Question", ""),
            "Response": r.get("Response", ""),
            "Type": r.get("Type", ""),
        })

if not data:
    st.warning("No responses found in Firestore.")
    st.stop()

df = pd.DataFrame(data)
st.success(f"Total Records Found: {len(df)}")

# ---------------- FILTERING ----------------
section_list = sorted(df["Section"].unique().tolist())
section = st.selectbox("Select Section", ["All"] + section_list)

if section != "All":
    df = df[df["Section"] == section]

# ---------------- STUDENT FILTER ----------------
student_list = sorted(df["Roll"].unique().tolist())
selected_student = st.selectbox("Select Student Roll Number", ["All"] + student_list)

if selected_student != "All":
    df = df[df["Roll"] == selected_student]

# ---------------- DISPLAY DATA ----------------
st.dataframe(df, use_container_width=True)

# =====================================================
# ✍️ MARK ENTRY FOR SHORT ANSWERS (Persistent)
# =====================================================
short_df = df[df["Type"] == "short"].copy()
if not short_df.empty:
    st.markdown("### ✍️ Manual Evaluation for Short Answers")

    marks_data = []
    for i, row in short_df.iterrows():
        q_text = row["Question"][:100] + ("..." if len(row["Question"]) > 100 else "")
        mark = st.number_input(
            f"Marks for {row['Roll']} – {row['QuestionID']} ({q_text})",
            min_value=0.0, max_value=10.0, step=0.5, key=f"mark_{i}"
        )
        marks_data.append({
            "Roll": row["Roll"],
            "QuestionID": row["QuestionID"],
            "Marks": mark,
            "Section": row["Section"],
            "Evaluator": "Faculty",
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    if st.button("💾 Save Marks"):
        for record in marks_data:
            doc_id = f"{record['Roll']}_{record['Section'].replace(' ', '_')}_{record['QuestionID']}"
            db.collection("short_marks").document(doc_id).set(record)
        st.success("✅ Marks saved successfully to Firestore!")

# =====================================================
# 🔄 LOAD EXISTING SHORT MARKS FROM FIRESTORE
# =====================================================
marks_docs = db.collection("short_marks").stream()
marks_records = [d.to_dict() for d in marks_docs]
marks_df = pd.DataFrame(marks_records) if marks_records else pd.DataFrame()

# =====================================================
# 📊 COMPUTE TOTALS AND SECTION-WISE AVERAGES
# =====================================================
likert_df = df[df["Type"].isin(["likert", "mcq"])].copy()
likert_df["ResponseNumeric"] = pd.to_numeric(likert_df["Response"], errors="coerce")

# Compute numeric means per section
section_scores = (
    likert_df.dropna(subset=["ResponseNumeric"])
    .groupby(["Roll", "Section"])["ResponseNumeric"]
    .mean()
    .reset_index()
    .rename(columns={"ResponseNumeric": "SectionScore"})
)

# Add short marks if available
if not marks_df.empty:
    short_sum = marks_df.groupby(["Roll", "Section"])["Marks"].sum().reset_index()
    section_scores = pd.concat([section_scores, short_sum], ignore_index=True)
    section_scores["Score"] = section_scores.get("SectionScore", 0) + section_scores.get("Marks", 0)
    section_scores["Score"].fillna(section_scores.get("Marks", section_scores.get("SectionScore")), inplace=True)
else:
    section_scores["Score"] = section_scores["SectionScore"]

# Student summary
if selected_student != "All":
    summary_df = section_scores[section_scores["Roll"] == selected_student].copy()
else:
    summary_df = section_scores.copy()

if not summary_df.empty:
    st.markdown("### 🧾 Section-wise Scores")
    st.dataframe(summary_df[["Roll", "Section", "Score"]], use_container_width=True)

    total_score = summary_df["Score"].sum()
    st.markdown(f"## 🏅 **Total Score for {selected_student if selected_student!='All' else 'All Students'}:** {total_score:.2f}")

# =====================================================
# 📈 VISUALIZATIONS
# =====================================================
st.markdown("### 📊 Performance Visualizations")

if not summary_df.empty:
    # Bar chart for section scores
    fig_bar = px.bar(
        summary_df,
        x="Section",
        y="Score",
        color="Section",
        text_auto=".2f",
        title=f"Section-wise Performance – {selected_student if selected_student!='All' else 'Overall'}"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Pie chart for proportional contribution
    fig_pie = px.pie(
        summary_df,
        names="Section",
        values="Score",
        title="Marks Distribution by Section"
    )
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("No numeric data available for visualization.")

# =====================================================
# 📤 EXPORT TO CSV
# =====================================================
st.markdown("### ⬇️ Download Consolidated Report")
csv = summary_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Report as CSV",
    data=csv,
    file_name=f"{selected_student if selected_student!='All' else 'all_students'}_summary.csv",
    mime="text/csv"
)
