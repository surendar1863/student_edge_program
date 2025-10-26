import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import plotly.express as px
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

if data:
    df = pd.DataFrame(data)
    st.success(f"Total Records Found: {len(df)}")

    # ---------------- FILTERING ----------------
    section_list = sorted(df["Section"].unique().tolist())
    section = st.selectbox("Select Section", ["All"] + section_list)

    filtered_df = df if section == "All" else df[df["Section"] == section]

    # ---------------- DISPLAY TABLE ----------------
    st.dataframe(filtered_df, use_container_width=True)

    # ---------------- VISUALIZATION SECTION ----------------
    st.markdown("### 📊 Data Visualizations")

    likert_df = filtered_df[filtered_df["Type"].isin(["likert", "mcq"])].copy()

    if not likert_df.empty:
        # Average Response per Section
        avg_scores = likert_df.groupby("Section")["Response"].mean().reset_index()
        st.plotly_chart(
            px.bar(
                avg_scores,
                x="Section",
                y="Response",
                color="Section",
                title="Average Scores by Section",
                text_auto=".2f"
            ),
            use_container_width=True
        )

        # Response distribution pie chart
        st.plotly_chart(
            px.pie(
                likert_df,
                names="Section",
                title="Response Distribution by Section"
            ),
            use_container_width=True
        )
    else:
        st.info("No Likert or MCQ data available for visualization.")

    # ---------------- MARK ENTRY FOR SHORT ANSWERS ----------------
    short_df = filtered_df[filtered_df["Type"] == "short"].copy()
    if not short_df.empty:
        st.markdown("### ✍️ Manual Evaluation for Short Answers")

        marks_data = []
        for i, row in short_df.iterrows():
            q_text = row["Question"][:80] + ("..." if len(row["Question"]) > 80 else "")
            mark = st.number_input(
                f"Marks for {row['Roll']} – {row['QuestionID']} ({q_text})",
                min_value=0.0, max_value=10.0, step=0.5, key=f"mark_{i}"
            )
            marks_data.append({
                "Roll": row["Roll"],
                "QuestionID": row["QuestionID"],
                "Marks": mark
            })

        if st.button("💾 Save Marks"):
            marks_df = pd.DataFrame(marks_data)
            st.session_state["short_marks"] = marks_df
            st.success("Marks recorded successfully! (You can later upload to Firestore if needed.)")

    # ---------------- EXPORT TO CSV ----------------
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv,
        file_name="student_responses.csv",
        mime="text/csv"
    )

else:
    st.warning("No responses found in Firestore.")
