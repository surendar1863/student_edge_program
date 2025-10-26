import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


st.set_page_config(page_title="Aptitude Dashboard", layout="wide")

st.title("📊 Aptitude Test Dashboard")

# Load data
df = pd.read_csv("results.csv")

# -----------------------------
# Summary Section
# -----------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Total Students", len(df))
col2.metric("Average Score", f"{df['Score'].mean():.2f}")
col3.metric("Max Score", df['Score'].max())

# -----------------------------
# Search Section
# -----------------------------
st.subheader("🔍 Search for Student")

search = st.text_input("Enter Student Name or Roll Number", "").strip().lower()

if search:
    filtered_df = df[df.apply(lambda row: search in str(row['Name']).lower() or search in str(row['Roll']).lower(), axis=1)]
else:
    filtered_df = df

# -----------------------------
# Student Table
# -----------------------------
filtered_df = filtered_df.reset_index(drop=True)
filtered_df.index = filtered_df.index + 1
st.write("### Students List (Click a row to view details)")
st.dataframe(filtered_df, width="stretch")

# -----------------------------
# Individual Visualization (Final Streamlit-Only Fix)
# -----------------------------
if not filtered_df.empty:
    st.write("### Individual Student Visualization")

    # Input to quickly find a student
    search_name = st.text_input("Enter Student Name or Roll No to find quickly", "").strip().lower()

    # --- Filter student list ---
    if search_name:
        matched_students = filtered_df[
            filtered_df.apply(
                lambda row: search_name in str(row["Name"]).lower() or search_name in str(row["Roll"]).lower(),
                axis=1,
            )
        ]
    else:
        matched_students = filtered_df

    if matched_students.empty:
        st.warning("No matching student found.")
    else:
        selected = st.selectbox("Select student to visualize", matched_students["Name"].unique(), index=0)
        student = df[df["Name"] == selected].iloc[0]

        st.success(f"Showing results for **{student['Name']}** ({student['Roll']})")

        # ---- Anchor marker for scrolling ----
        scroll_anchor = st.empty()  # invisible placeholder
        scroll_anchor.markdown("<div id='chart_start'></div>", unsafe_allow_html=True)

        # ---- Charts ----
        fig_pie = go.Figure(
            go.Pie(
                labels=["Correct", "Incorrect"],
                values=[student["Score"], student["Total"] - student["Score"]],
                hole=0.5,
                marker_colors=["#4CAF50", "#E74C3C"],
            )
        )
        fig_pie.update_layout(title_text="Score Distribution", width=420, height=350)

        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=student["Score"],
                title={"text": "Student Score"},
                gauge={
                    "axis": {"range": [0, student["Total"]]},
                    "bar": {"color": "#4CAF50"},
                    "steps": [
                        {"range": [0, student["Total"] * 0.5], "color": "#FFDDDD"},
                        {"range": [student["Total"] * 0.5, student["Total"]], "color": "#D4EFDF"},
                    ],
                },
            )
        )
        fig_gauge.update_layout(width=420, height=350)

        col1, col2 = st.columns(2)
        col1.plotly_chart(fig_pie, config={"displayModeBar": False})
        col2.plotly_chart(fig_gauge, config={"displayModeBar": False})

        # ---- Scroll the chart into view (pure Streamlit way) ----
        # When user presses Enter, Streamlit reruns from top — we re-render here,
        # so this block executes after rerun and scrolls immediately to the anchor
        st.markdown(
            """
            <script>
                document.getElementById('chart_start').scrollIntoView({behavior: 'smooth', block: 'start'});
            </script>
            """,
            unsafe_allow_html=True,
        )
