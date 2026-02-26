import google.generativeai as genai
import pandas as pd
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def dataframe_context(df: pd.DataFrame):
    return f"""
Dataset shape: {df.shape}

Columns:
{list(df.columns)}

Data types:
{df.dtypes.to_string()}

Sample rows:
{df.head(5).to_string()}
"""

def ask_gemini(df, question):

    context = dataframe_context(df)

    prompt = f"""
You are a business data analyst.

DATASET:
{context}

QUESTION:
{question}

Give:
1. Answer
2. Insight
3. Suggested chart
"""

    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(prompt)

    return response.text