"""
Streamlit Frontend for NL-to-SQL Business Analyst Agent.
Interacts with the FastAPI backend to provide an interactive dashboard with
natural language query inputs, SQL inspection, data tables, and Plotly visualizations.
"""

import os
import requests
from decimal import Decimal
import pandas as pd
import plotly.express as px
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="NL-to-SQL Business Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished, executive styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .answer-card {
        background-color: #F8FAFC;
        border-left: 5px solid #3B82F6;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-badge {
        display: inline-block;
        background-color: #EFF6FF;
        color: #1D4ED8;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar Configuration & Schema Explorer
# ---------------------------------------------------------------------------

st.sidebar.title("⚙️ Configuration")
api_base_url = st.sidebar.text_input("FastAPI Backend URL", value="http://localhost:8001")

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 System Status")

# Check Health
health_url = f"{api_base_url.rstrip('/')}/health"
schema_url = f"{api_base_url.rstrip('/')}/schema"

try:
    health_resp = requests.get(health_url, timeout=3)
    if health_resp.status_code == 200:
        health_data = health_resp.json()
        st.sidebar.success(f"🟢 Backend: {health_data.get('status', 'OK').upper()}")
        st.sidebar.success(f"🗄️ PostgreSQL: {health_data.get('database', 'Connected').upper()}")
        st.sidebar.info(f"📊 Active Tables: {health_data.get('tables_count', 0)}")
    else:
        st.sidebar.warning("🟡 Backend status: degraded")
except Exception:
    st.sidebar.error("🔴 Backend offline. Make sure FastAPI server is running on port 8001.")

st.sidebar.markdown("---")
st.sidebar.subheader("💡 Sample Business Questions")

sample_questions = [
    "Which city has the most customers?",
    "What is the total revenue by product category?",
    "Who are the top customers by total order spending?",
    "What are the top 3 best-selling products by quantity?",
    "Show all orders placed in August 2026 with customer names.",
]

for q in sample_questions:
    if st.sidebar.button(f"📌 {q}", key=f"btn_{q}"):
        st.session_state["query_input"] = q

# Schema viewer in sidebar
st.sidebar.markdown("---")
with st.sidebar.expander("🔍 View Database Schema"):
    try:
        schema_resp = requests.get(schema_url, timeout=3)
        if schema_resp.status_code == 200:
            st.code(schema_resp.json().get("schema_text", "No schema available"), language="yaml")
        else:
            st.write("Could not retrieve schema.")
    except Exception:
        st.write("Schema unavailable (backend unreachable).")


# ---------------------------------------------------------------------------
# Main Content Area
# ---------------------------------------------------------------------------

st.markdown('<div class="main-header">📊 NL-to-SQL Business Analyst Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Ask natural language business questions to autonomously generate PostgreSQL queries, '
    'inspect live execution results, and receive synthesized executive insights.</div>',
    unsafe_allow_html=True,
)

# Input container
query_default = st.session_state.get("query_input", "")
user_question = st.text_input(
    "Enter your business question:",
    value=query_default,
    placeholder="e.g., Which city has the highest customer count?",
    key="main_question_input",
)

col1, col2 = st.columns([1, 5])
with col1:
    ask_button = st.button("🚀 Ask Question", type="primary", use_container_width=True)
with col2:
    if st.button("🔄 Clear", use_container_width=False):
        st.session_state["query_input"] = ""
        st.rerun()

if ask_button and user_question.strip():
    ask_url = f"{api_base_url.rstrip('/')}/ask"
    
    with st.spinner("🤖 Agent is analyzing schema, generating SQL, executing, and synthesizing answer..."):
        try:
            response = requests.post(
                ask_url,
                json={"question": user_question.strip(), "max_retries": 2},
                timeout=30,
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "")
                sql = data.get("sql", "")
                columns = data.get("columns", [])
                rows = data.get("rows", [])
                error = data.get("error")
                retry_count = data.get("retry_count", 0)
                
                # Executive Summary Display
                if answer:
                    st.markdown("### 📋 Executive Summary")
                    st.markdown(f'<div class="answer-card"><div style="font-size: 1.15rem; color: #1F2937; line-height: 1.6;">{answer}</div></div>', unsafe_allow_html=True)

                # Security / Execution Warning Display
                if error:
                    st.warning(f"⚠️ **Security Guardrail Notice:** {error}")
                    if sql and sql != "REJECTED_NON_SELECT_INTENT":
                        with st.expander("🛠️ Attempted SQL Query", expanded=True):
                            st.code(sql, language="sql")
                else:
                    # Metadata badges
                    badges_html = f'<span class="metric-badge">📊 {len(rows)} Row(s)</span>'
                    if retry_count > 0:
                        badges_html += f'<span class="metric-badge">🔄 Self-Corrected ({retry_count} retry)</span>'
                    else:
                        badges_html += '<span class="metric-badge">✨ 1-Shot Accurate SQL</span>'
                    st.markdown(badges_html, unsafe_allow_html=True)
                    st.markdown("")

                    # SQL Details Expander
                    with st.expander("🔍 Generated PostgreSQL Query", expanded=False):
                        st.code(sql, language="sql")

                    # Data Table Expander
                    if rows:
                        df = pd.DataFrame(rows)
                        with st.expander("📄 Raw Database Results", expanded=True):
                            st.dataframe(df, use_container_width=True)

                        # Visualization Section (Plotly)
                        # Automatically convert Decimal objects and stringified numbers to numeric types
                        clean_df = df.copy()
                        for col in clean_df.columns:
                            clean_df[col] = clean_df[col].apply(lambda v: float(v) if isinstance(v, Decimal) else v)
                            converted = pd.to_numeric(clean_df[col], errors="coerce")
                            if converted.notna().sum() > 0 and converted.notna().sum() == clean_df[col].notna().sum():
                                clean_df[col] = converted

                        # Identify numeric metric columns (prefer non-ID columns)
                        all_numeric = clean_df.select_dtypes(include=["number"]).columns.tolist()
                        metric_cols = [c for c in all_numeric if not c.lower().endswith("_id")]
                        if not metric_cols and all_numeric:
                            metric_cols = all_numeric

                        # Only show charts for multi-row results with at least one numeric metric and dimension
                        if len(clean_df) > 1 and metric_cols and len(clean_df.columns) >= 2:
                            metric_col = metric_cols[0]

                            # Detect Date / Time columns
                            date_cols = []
                            for col in clean_df.columns:
                                if col == metric_col:
                                    continue
                                if pd.api.types.is_datetime64_any_dtype(clean_df[col]):
                                    date_cols.append(col)
                                elif any(term in col.lower() for term in ["date", "time", "month", "year", "day"]):
                                    try:
                                        parsed = pd.to_datetime(clean_df[col], errors="coerce")
                                        if parsed.notna().sum() > 0 and parsed.notna().sum() == clean_df[col].notna().sum():
                                            date_cols.append(col)
                                    except Exception:
                                        pass

                            # Detect Categorical / Dimension column
                            non_metric_cols = [c for c in clean_df.columns if c != metric_col and not c.lower().endswith("_id")]
                            if not non_metric_cols:
                                non_metric_cols = [c for c in clean_df.columns if c != metric_col]

                            if non_metric_cols:
                                st.markdown("### 📈 Visual Analysis")

                                if date_cols:
                                    # Date/Time + Numeric -> Line Chart
                                    date_col = date_cols[0]
                                    fig_line = px.line(
                                        clean_df,
                                        x=date_col,
                                        y=metric_col,
                                        markers=True,
                                        title=f"{metric_col.replace('_', ' ').title()} over {date_col.replace('_', ' ').title()}",
                                    )
                                    fig_line.update_layout(
                                        margin=dict(l=20, r=20, t=40, b=20),
                                        paper_bgcolor="rgba(0,0,0,0)",
                                        plot_bgcolor="rgba(0,0,0,0)",
                                    )
                                    st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})
                                else:
                                    # Categorical + Numeric -> Bar Chart
                                    label_col = non_metric_cols[0]
                                    fig_bar = px.bar(
                                        clean_df,
                                        x=label_col,
                                        y=metric_col,
                                        color=label_col if len(clean_df) <= 12 else None,
                                        title=f"{metric_col.replace('_', ' ').title()} by {label_col.replace('_', ' ').title()}",
                                    )
                                    fig_bar.update_layout(
                                        margin=dict(l=20, r=20, t=40, b=20),
                                        paper_bgcolor="rgba(0,0,0,0)",
                                        plot_bgcolor="rgba(0,0,0,0)",
                                    )
                                    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
                    else:
                        st.info("Query returned 0 rows from the database.")
            else:
                st.error(f"Backend returned HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to FastAPI backend. Please ensure `uvicorn app.main:app --reload --port 8001` is running on port 8001.")
        except Exception as e:
            st.error(f"❌ An unexpected error occurred: {str(e)}")
elif ask_button and not user_question.strip():
    st.warning("Please enter a question before clicking Ask.")
