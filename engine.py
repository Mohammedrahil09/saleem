import pandas as pd
import calendar
import re
from rapidfuzz import process
from openai import OpenAI
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


# helper function for frontend
def run_query(df, question):
    engine = SmartAnalyticsEngine(df)
    parsed = engine.parse_question(question)
    return engine.execute_query(parsed)

def ask_ai(df, question):
    # Initialize the OpenRouter client
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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"
    )

    prompt = f"""
    You are a senior data analyst You MUST respond entirely in English.

    Dataset columns:
    {list(df.columns)}

    Dataset sample:
    {df.head(5).to_string()}

    User question:
    {question}

    Provide:
    - insights
    - trends
    - anomalies
    - business suggestions
    """

    # Automatically routes to an available free model
    response = client.chat.completions.create(
        model="openrouter/free", 
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content