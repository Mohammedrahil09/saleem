import pandas as pd
import calendar
import re
from rapidfuzz import process
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


class SmartAnalyticsEngine:

    def __init__(self, df):
        self.df = df.copy()
        self.columns = df.columns.tolist()
        self.lower_columns = [c.lower() for c in self.columns]

        # Detect date columns
        self.date_columns = [
            col for col in self.columns
            if pd.api.types.is_datetime64_any_dtype(df[col])
        ]

    # -----------------------------
    # SMART COLUMN MATCHING
    # -----------------------------
    def match_column(self, word):
        word = word.lower()

        if word in self.lower_columns:
            return self.columns[self.lower_columns.index(word)]

        match, score, _ = process.extractOne(word, self.lower_columns)
        if score > 85:
            return self.columns[self.lower_columns.index(match)]

        return None

    # -----------------------------
    # NLP PARSER
    # -----------------------------
    def parse_question(self, question):

        question_lower = question.lower()

        parsed = {
            "aggregation": None,
            "metric": None,
            "filters": [],
            "time_filter": {}
        }

        agg_map = {
            "total": "sum",
            "sum": "sum",
            "average": "mean",
            "mean": "mean",
            "count": "count",
            "max": "max",
            "min": "min"
        }

        for key in agg_map:
            if key in question_lower:
                parsed["aggregation"] = agg_map[key]
                break

        # Detect numeric metric
        for col in self.columns:
            if col.lower() in question_lower and pd.api.types.is_numeric_dtype(self.df[col]):
                parsed["metric"] = col
                break

        # Month detection
        month_map = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
        for month_name, month_num in month_map.items():
            if month_name in question_lower:
                parsed["time_filter"]["month"] = month_num
                break

        # Year detection
        year_match = re.search(r"(20\d{2})", question_lower)
        if year_match:
            parsed["time_filter"]["year"] = int(year_match.group(1))

        # Categorical filters
        for col in self.columns:
            if self.df[col].dtype == "object":
                for val in self.df[col].dropna().unique():
                    if str(val).lower() in question_lower:
                        parsed["filters"].append({
                            "column": col,
                            "value": val
                        })

        return parsed

    # -----------------------------
    # EXECUTE QUERY
    # -----------------------------
    def execute_query(self, parsed):

        result = self.df.copy()

        for f in parsed["filters"]:
            result = result[result[f["column"]] == f["value"]]

        if parsed["time_filter"] and self.date_columns:
            date_col = self.date_columns[0]

            if "year" in parsed["time_filter"]:
                result = result[result[date_col].dt.year == parsed["time_filter"]["year"]]

            if "month" in parsed["time_filter"]:
                result = result[result[date_col].dt.month == parsed["time_filter"]["month"]]

        if parsed["aggregation"] and parsed["metric"]:
            agg_func = parsed["aggregation"]
            value = getattr(result[parsed["metric"]], agg_func)()
            return pd.DataFrame({f"{agg_func}_{parsed['metric']}": [value]})

        return result


# -----------------------------
# HELPER FUNCTION
# -----------------------------
def run_query(df, question):
    engine = SmartAnalyticsEngine(df)
    parsed = engine.parse_question(question)
    return engine.execute_query(parsed)


# -----------------------------
# OPENROUTER AI FUNCTION
# -----------------------------
def ask_ai(df, question):

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

    prompt = f"""
You are a senior business data analyst.

DATASET COLUMNS:
{list(df.columns)}

SAMPLE DATA:
{df.head(5).to_string()}

USER QUESTION:
{question}

Provide:
1. Direct answer
2. Key insights
3. Trends
4. Anomalies
5. Business recommendations
"""

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",  # 🔥 reliable free model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        result = response.choices[0].message.content

        if not result:
            return "⚠️ AI returned an empty response. Try rephrasing your question."

        return result

    except Exception as e:
        return f"❌ AI Error: {str(e)}"