import pandas as pd
from openai import OpenAI
import os

# Uses environment variable OPENAI_API_KEY
client = OpenAI()

def dataframe_context(df: pd.DataFrame):

    # Keep context small so API is fast + cheap
    summary = f"""
Dataset shape: {df.shape}

Columns:
{list(df.columns)}

Data types:
{df.dtypes.to_string()}

Sample rows:
{df.head(5).to_string()}
"""
    return summary


def ask_genai(df: pd.DataFrame, question: str):

    context = dataframe_context(df)

    prompt = f"""
You are a senior business data analyst.

DATASET INFO:
{context}

USER QUESTION:
{question}

Respond in this format:

1. Direct Answer  
2. Business Insight  
3. Suggested chart (if useful)  
4. Any risks or anomalies noticed
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return response.choices[0].message.content