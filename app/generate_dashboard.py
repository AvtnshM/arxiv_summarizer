import streamlit as st
import pandas as pd
import os

# --- Page Setup ---
st.set_page_config(page_title="📚 ArXiv Paper Summaries", layout="wide")
st.title("🧠 ArXiv Paper Summaries Dashboard")

# --- Load Data ---
@st.cache_data
def load_data():
    """
    Load and prepare the summarized papers data.
    
    CHANGES MADE:
    1. Use 'summary' column explicitly (contains full paper summaries)
    2. Handle multiline text and special characters properly
    3. Strip any intro text like "Here's a summary..."
    4. Ensure empty summaries show placeholder text
    
    Returns:
        pd.DataFrame: Cleaned dataframe with summary_text column
    """
    csv_path = "data/processed/summarized.csv"
    if not os.path.exists(csv_path):
        st.error("❌ summarized.csv not found! Please run summarizer first.")
        st.stop()

    df = pd.read_csv(csv_path)

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # FIXED: Use the 'summary' column directly - it has the full summary text
    if "summary" in df.columns:
        df["summary_text"] = df["summary"].fillna("").astype(str)
    elif "summary_short" in df.columns:
        df["summary_text"] = df["summary_short"].fillna("").astype(str)
    else:
        df["summary_text"] = ""

    # Clean summaries — remove prefix like "Here's a summary..." and extra whitespace
    df["summary_text"] = (
        df["summary_text"]
        .str.replace(r"(?i)^here.?s a summary.*?:\s*", "", regex=True)
        .str.replace(r"\n+", " ", regex=True)  # Replace newlines with spaces
        .str.replace(r"\s+", " ", regex=True)  # Replace multiple spaces with single space
        .str.strip()
    )

    # Clean key columns
    for col in ["title", "authors", "category", "link"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)

    return df


df = load_data()

# --- Debug info (comment out after fixing) ---
# st.write("DEBUG - Available columns:", df.columns.tolist())
# st.write("DEBUG - First summary:", df["summary_text"].iloc[0][:200] if len(df) > 0 else "No data")

# --- Filters ---
categories = sorted(df["category"].dropna().unique())
selected_category = st.selectbox("📂 Select Category", ["All"] + categories)
search_term = st.text_input("🔍 Search by Title or Author")

filtered_df = df.copy()

if selected_category != "All":
    filtered_df = filtered_df[filtered_df["category"] == selected_category]

if search_term:
    filtered_df = filtered_df[
        filtered_df["title"].str.contains(search_term, case=False, na=False)
        | filtered_df["authors"].str.contains(search_term, case=False, na=False)
    ]

st.markdown(f"### Showing {len(filtered_df)} papers")

# --- Dynamic layout width based on summary length ---
def get_card_width(summary):
    """
    Calculate card width based on summary length for better readability.
    
    Args:
        summary (str): The summary text
        
    Returns:
        str: CSS width value (e.g., "70%")
    """
    length = len(summary)
    if length < 400:
        return "70%"
    elif length < 800:
        return "85%"
    else:
        return "95%"

# --- Display Papers ---
for _, row in filtered_df.iterrows():
    summary_text = row.get("summary_text", "").strip()
    
    # FIXED: Better check for empty summaries
    if not summary_text or len(summary_text) < 10:
        summary_text = "<i>No summary available.</i>"

    card_width = get_card_width(summary_text)

    st.markdown(
        f"""
        <div style="
            background-color:#ffffff;
            padding:16px 22px;
            border-radius:12px;
            margin-bottom:15px;
            box-shadow:0 3px 8px rgba(0,0,0,0.08);
            border-left:6px solid #1a73e8;
            width:{card_width};
            transition: all 0.2s ease-in-out;
        ">
            <h4 style="color:#1a73e8;margin-bottom:10px;">{row['title']}</h4>
            <p style="font-size:15px;line-height:1.55;color:#333;text-align:justify;
                      margin-bottom:8px;">
                {summary_text}
            </p>
            <p style="font-size:14px;color:#555;margin-top:4px;">
                <b>Authors:</b> {row['authors']}<br>
                <b>Category:</b> {row['category']}
            </p>
            <a href="{row['link']}" target="_blank" 
               style="color:#0b66c2;font-weight:bold;text-decoration:none;">
               🔗 Read full paper
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )