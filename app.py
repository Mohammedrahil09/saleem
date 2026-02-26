import streamlit as st
import pandas as pd
from engine import run_query, SmartAnalyticsEngine, ask_ai          
import base64
import io

st.set_page_config(page_title="Smart Analytics Engine", layout="wide")

def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return "" # Fallback if image isn't found

bg_img = get_base64("background.jpeg")

# Inject Custom CSS to match the new screenshots
st.markdown(f"""
<style>
    /* Main Background & Base Text */
    .stApp {{
        background-image: url("data:image/jpeg;base64,{bg_img}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #1e293b;
    }}
    
    /* Header styling */
    h1, h2, h3 {{
        color: #0f172a !important;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }}

    /* Center Main Title */
    h1 {{
        text-align: center;
        margin-bottom: 10px;
    }}

    /* Normal sizing for Radio Group Labels */
    div[data-testid="stRadio"] > label {{
        font-size: 14px;
        color: #0f172a !important;
        margin-bottom: 5px;
        font-weight: 500;
    }}

    /* Transform Radio Buttons into Gradient Blocks with Wrapping */
    div[role="radiogroup"] {{
        display: flex;
        flex-direction: row;
        gap: 15px;
        flex-wrap: wrap;
    }}

    div[role="radiogroup"] > label {{
        background: linear-gradient(90deg, #ff8a00, #e52e71) !important;
        border-radius: 8px;
        padding: 10px 15px;
        width: 130px; /* Forces text wrapping as seen in screenshots */
        min-height: 55px;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        cursor: pointer;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 0 !important;
        transition: transform 0.2s;
    }}

    div[role="radiogroup"] > label:hover {{
        transform: translateY(-2px);
    }}

    div[role="radiogroup"] > label p {{
        color: white !important;
        font-weight: bold;
        font-size: 14px;
        margin: 0 0 0 8px;
        white-space: normal; /* Allows text to break to new line */
        line-height: 1.2;
    }}

    /* Radio Circle Visibility and Styling */
    div[role="radiogroup"] label div[data-baseweb="radio"] > div {{
        background-color: transparent !important;
        border: 2px solid white !important;
    }}

    /* Fill inner circle when checked */
    div[role="radiogroup"] label[data-checked="true"] div[data-baseweb="radio"] > div > div {{
        background-color: white !important;
    }}

    /* File Uploader styling */
    [data-testid="stFileUploader"] {{
        max-width: 600px;
        background-color: rgba(255, 255, 255, 0.85);
        border-radius: 10px;
        padding: 15px;
        margin-top: 15px;
    }}

    /* Dataframe background */
    [data-testid="stDataFrame"] {{
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
    }}

    /* Primary and Secondary Buttons */
    div.stButton > button {{
        background: linear-gradient(90deg, #ff8a00, #e52e71);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    
    div.stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(229, 46, 113, 0.4);
        color: white;
        border: none;
    }}

    /* Download Buttons */
    div.stDownloadButton > button {{
        background: linear-gradient(90deg, #11998e, #38ef7d);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: transform 0.2s, box-shadow 0.2s;
    }}

    div.stDownloadButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(56, 239, 125, 0.4);
        color: white;
        border: none;
    }}

    /* Success Message Styling adjustments */
    [data-testid="stAlert"] {{
        background-color: rgba(17, 153, 142, 0.2);
        color: #0f172a;
        font-weight: 500;
        border: none;
    }}
</style>
""", unsafe_allow_html=True)

st.title("📊 Smart Analytics Engine")


data_source_opt = st.radio(
    "Choose Data Source",
    ["Upload Excel File(s)", "Connect to Database"],
    horizontal=True
)

if 'df' not in st.session_state:
    st.session_state['df'] = None
if 'query_result' not in st.session_state:
    st.session_state['query_result'] = None

# =========================================================
# HELPER FUNCTION FOR RELATIONSHIP JOINS
# =========================================================
def build_manual_relationship(dfs_dict):

    st.subheader("🔗 Build Table Relationships")

    table_names = list(dfs_dict.keys())

    base_table = st.selectbox("Select Base Table", table_names)
    merged_df = dfs_dict[base_table]

    remaining_tables = [t for t in table_names if t != base_table]

    for tbl in remaining_tables:

        with st.expander(f"Join {tbl}"):

            enable_join = st.checkbox(f"Join {tbl} to {base_table}", key=f"join_{tbl}")

            if enable_join:

                left_col = st.selectbox(
                    f"{base_table} column",
                    merged_df.columns,
                    key=f"left_{tbl}"
                )

                right_col = st.selectbox(
                    f"{tbl} column",
                    dfs_dict[tbl].columns,
                    key=f"right_{tbl}"
                )

                join_type = st.selectbox(
                    "Join type",
                    ["inner", "left", "right", "outer"],
                    key=f"type_{tbl}"
                )

                try:
                    merged_df = merged_df.merge(
                        dfs_dict[tbl],
                        left_on=left_col,
                        right_on=right_col,
                        how=join_type
                    )
                except Exception as e:
                    st.error(f"Join failed: {e}")

    return merged_df

# =========================================================
# MULTIPLE FILE UPLOAD
# =========================================================
if data_source_opt == "Upload Excel File(s)":

    uploaded_files = st.file_uploader(
        "Upload Excel/CSV file(s)",
        type=["xlsx", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:

        dfs_dict = {}

        for file in uploaded_files:
            try:
                if file.name.endswith(".csv"):
                    dfs_dict[file.name] = pd.read_csv(file)
                else:
                    dfs_dict[file.name] = pd.read_excel(file)
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")

        if len(dfs_dict) == 1:
            st.session_state['df'] = list(dfs_dict.values())[0]

        else:
            combine_mode = st.radio(
                "How do you want to combine files?",
                ["Append (same columns)", "Manual Relationship Join"],
                horizontal=True
            )

            if combine_mode == "Append (same columns)":
                st.session_state['df'] = pd.concat(dfs_dict.values(), ignore_index=True)

            else:
                st.session_state['df'] = build_manual_relationship(dfs_dict)

    else:
        st.session_state['df'] = None

# =========================================================
# DATABASE MULTI QUERY
# =========================================================
elif data_source_opt == "Connect to Database":

    st.info("Example URI: sqlite:///mydatabase.db or postgresql://user:password@localhost/mydb")
    db_uri = st.text_input("Database URI")

    sql_queries = st.text_area(
        "Enter SQL queries (one per line)",
        height=150,
        placeholder="SELECT * FROM Orders\nSELECT * FROM Customers\nSELECT * FROM Products"
    )

    if st.button("Connect & Fetch Data") and db_uri and sql_queries:
        try:
            import sqlalchemy as sa
            engine = sa.create_engine(db_uri)

            dfs_dict = {}

            for i, q in enumerate(sql_queries.split("\n")):
                q = q.strip()
                if q:
                    dfs_dict[f"Query_{i+1}"] = pd.read_sql(q, engine)

            if len(dfs_dict) == 1:
                st.session_state['df'] = list(dfs_dict.values())[0]

            else:
                combine_mode = st.radio(
                    "How do you want to combine tables?",
                    ["Append", "Manual Relationship Join"],
                    horizontal=True
                )

                if combine_mode == "Append":
                    st.session_state['df'] = pd.concat(dfs_dict.values(), ignore_index=True)
                else:
                    st.session_state['df'] = build_manual_relationship(dfs_dict)

        except Exception as e:
            st.error(f"Failed to fetch data: {e}")

df = st.session_state['df']

if df is not None:

    # Auto-detect date columns
    for col in df.columns:
        if "date" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except:
                pass

    st.success("File uploaded successfully!")

    st.subheader("Preview")
    st.dataframe(df.head(), use_container_width=True)

    # Ask question
    st.subheader("Ask AI Question")
    question = st.text_input("Type your question")

    if st.button("Run Query") and question:
        st.session_state['query_result'] = run_query(df, question)
        
    if st.session_state['query_result'] is not None:
        st.subheader("Result")
        st.dataframe(st.session_state['query_result'], use_container_width=True)

        st.download_button(
            "Download Result",
            st.session_state['query_result'].to_csv(index=False).encode('utf-8'),
            "result.csv",
            key="download_query_result"
        )

    # Dynamic filter
    st.subheader("Filter Data")

    filtered_df = df.copy()

    # Let user pick which columns to filter on
    filter_cols = st.multiselect("Filter dataframe on", df.columns)
    
    for col in filter_cols:
        # Datetime
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            target_date = st.date_input(f"Select date for {col}", value=None)
            if target_date:
                filtered_df = filtered_df[filtered_df[col].dt.date == target_date]
        
        # Categorical / Object / String
        elif pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            unique_vals = df[col].dropna().unique()
            selected_vals = st.multiselect(f"Select values for {col}", unique_vals)
            if selected_vals:
                filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]
                
        # Numeric
        elif pd.api.types.is_numeric_dtype(df[col]):
            try:
                _min = float(df[col].dropna().min())
                _max = float(df[col].dropna().max())
                
                if _min < _max:
                    selected_range = st.slider(f"Select range for {col}", min_value=_min, max_value=_max, value=(_min, _max))
                    filtered_df = filtered_df[(df[col] >= selected_range[0]) & (df[col] <= selected_range[1])]
                else:
                    st.info(f"Column '{col}' has a constant value of {_min}")
            except Exception:
                st.info(f"Could not filter numeric column '{col}'")

    st.subheader("Filtered Data")
    display_cols = st.multiselect("Choose columns to display", df.columns, default=df.columns[:5])
    if display_cols:
        final_df = filtered_df[display_cols]
    else:
        final_df = filtered_df

    st.dataframe(final_df, use_container_width=True)

    download_format = st.radio("Download Format", ["CSV", "Excel"], horizontal=True)

    if download_format == "CSV":
        st.download_button(
            "Download Filtered Data",
            final_df.to_csv(index=False).encode('utf-8'),
            "filtered.csv",
            key="download_filtered_data_csv"
        )
    else:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Filtered Data')
        
        st.download_button(
            "Download Filtered Data",
            buffer.getvalue(),
            "filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_filtered_data_excel"
        )

    # Dynamic Dashboard Creation
    st.subheader("📈 Dynamic Dashboard")
    
    # We only show the dashboard if there are columns to plot
    if len(final_df.columns) >= 2:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            chart_type = st.selectbox("Chart Type", ["Bar Chart", "Line Chart", "Scatter Plot", "Area Chart"])
        with col2:
            x_axis = st.selectbox("X-Axis (Categorical/Time)", final_df.columns, index=0)
        with col3:
            # Try to default Y-axis to a numeric column if available
            numeric_cols = final_df.select_dtypes(include='number').columns.tolist()
            if numeric_cols and numeric_cols[0] in final_df.columns:
                default_y_index = list(final_df.columns).index(numeric_cols[0])
            elif len(final_df.columns) > 1:
                default_y_index = 1
            else:
                default_y_index = 0
                
            y_axis = st.selectbox("Y-Axis (Numeric)", final_df.columns, index=default_y_index)
            
        st.write(f"Displaying **{chart_type}** for `{y_axis}` over `{x_axis}`")
        
        # Prepare data for plotting (aggregate if necessary depending on the chart)
        # Use streamlit native charts
        if chart_type == "Bar Chart":
            st.bar_chart(final_df, x=x_axis, y=y_axis)
        elif chart_type == "Line Chart":
            st.line_chart(final_df, x=x_axis, y=y_axis)
        elif chart_type == "Scatter Plot":
            st.scatter_chart(final_df, x=x_axis, y=y_axis)
        elif chart_type == "Area Chart":
            st.area_chart(final_df, x=x_axis, y=y_axis)
            
    else:
        st.info("Need at least 2 columns in the dataset to generate a dashboard.")
        # =========================================================
# 🤖 GENAI DATA ASSISTANT
# =========================================================

st.subheader("🤖 AI Data Assistant")
if st.button("Ask AI"):
    if question:
        with st.spinner("AI analyzing your data..."):
            try:
                ai_result = ask_ai(df, question)
                st.markdown("### 🤖 AI Insights")
                st.write(ai_result)
            except Exception as e:
                st.error(f"AI Error: {e}")

if df is not None:

    # Chat memory
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_msg = st.text_input("Ask anything about your dataset")

    col1, col2 = st.columns([1,5])
    with col1:
        ask_btn = st.button("ask_ai_btn")

    if ask_btn and user_msg:

        with st.spinner("AI analyzing your data..."):
            try:
                # We changed "ask_gemini" to "ask_ai" right here:
                reply = ask_ai(final_df, user_msg) 
            except Exception as e:
                reply = f"AI Error: {e}"

        st.session_state.chat_history.append(("You", user_msg))
        st.session_state.chat_history.append(("AI", reply))

    # Show chat history
    for role, msg in st.session_state.chat_history:
        if role == "You":
            st.markdown(f"**🧑 You:** {msg}")
        else:
            st.markdown(f"**🤖 AI:** {msg}")

else:
    st.info("Upload data to enable AI assistant.")