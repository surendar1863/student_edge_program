import streamlit as st
import pandas as pd
import os

st.title("Aptitude Test Assessment")

name = st.text_input("Enter your name")
roll = st.text_input("Enter your roll number")

# Load questions from CSV
questions_df = pd.read_csv("aptitude_questions.csv")

st.subheader("Answer the following:")

score = 0
for i, row in questions_df.iterrows():
    q = row["Question"]
    options = [row["Option1"], row["Option2"], row["Option3"], row["Option4"]]
    correct = row["Correct"]
    ans = st.radio(f"{i+1}. {q}", options, key=i)
    if ans == correct:
        score += 1

if st.button("Submit"):
    result = {"Name": name, "Roll": roll, "Score": score, "Total": len(questions_df)}
    df = pd.DataFrame([result])

    if not os.path.exists("results.csv"):
        df.to_csv("results.csv", index=False)
    else:
        df_existing = pd.read_csv("results.csv")
        df_all = pd.concat([df_existing, df], ignore_index=True)
        df_all.to_csv("results.csv", index=False)

    st.info("Your result has been saved successfully!")
