import requests
import pandas as pd

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

def ask_local_ai(df, question):

    context = dataframe_context(df)

    prompt = f"""
You are a senior business data analyst.

DATASET:
{context}

QUESTION:
{question}

Give:
1. Direct answer
2. Business insight
3. Suggested chart if useful
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]