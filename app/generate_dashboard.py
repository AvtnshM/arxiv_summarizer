# app/generate_dashboard.py
"""
Streamlit dashboard for ArXiv Paper Summaries.

Features:
- Loads data/processed/summarized.csv (expects LLM-generated summary in 'summary')
- Shows total processed, filtering, and table view
- Displays latest summary generation timestamp and week
- Per-paper regenerate using Groq LLM (if GROQ_API_KEY present)
- Dispatch GitHub Actions workflow via API (requires GH_PAT + REPO_OWNER + REPO_NAME in .env)
- Server-side "Regenerate newsletter PDF" button (runs newsletter_generator.py)
- Download button for output/newsletter.pdf if available
"""
import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import subprocess
import requests
import time

sys.stdout.reconfigure(encoding="utf-8")

# Optional LLM client import (Groq). If not installed, LLM features are disabled.
try:
    from groq import Groq
except Exception:
    Groq = None

# Load environment from repo root .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

st.set_page_config(page_title="📚 ArXiv Paper Summaries", layout="wide")
st.title("🧠 ArXiv Paper Summaries Dashboard")

CSV_PATH = "data/processed/summarized.csv"
RAW_PATH = "data/raw/papers.csv"
PDF_PATH = "output/newsletter.pdf"

# --- Utilities ---
def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()

def human_ts(iso_ts):
    try:
        return pd.to_datetime(iso_ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_ts or ""

def week_of_iso(iso_ts):
    try:
        dt = pd.to_datetime(iso_ts)
        monday = dt - pd.Timedelta(days=dt.dayofweek)
        return f"Week of {monday.date().isoformat()}"
    except Exception:
        return ""

# --- Data loaders ---
@st.cache_data
def load_processed():
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
    else:
        df = pd.DataFrame()
    # Normalize & ensure columns exist
    if not df.empty:
        df.columns = [c.strip() for c in df.columns]
        if "summary" not in df.columns and "summary_short" in df.columns:
            df["summary"] = df["summary_short"]
        for c in ["title", "authors", "category", "link", "summary", "summary_updated", "week_of_update"]:
            if c not in df.columns:
                df[c] = ""
    return df

@st.cache_data
def load_raw():
    if os.path.exists(RAW_PATH):
        return pd.read_csv(RAW_PATH)
    return pd.DataFrame()

proc = load_processed()
raw = load_raw()

# Sidebar: Controls
st.sidebar.header("Controls")
st.sidebar.markdown("Use LLM to generate missing summaries (costs tokens). Prefer bulk GH Action runs for full corpus.")

# --- GitHub Actions dispatch ---
st.sidebar.subheader("Pipeline / Refresh")
if st.sidebar.button("🔁 Dispatch pipeline (GitHub Actions)"):
    GH_PAT = os.getenv("GH_PAT")
    REPO_OWNER = os.getenv("REPO_OWNER")
    REPO_NAME = os.getenv("REPO_NAME")
    WORKFLOW_FILE = os.getenv("WORKFLOW_FILE", "run_pipeline.yml")
    REF = os.getenv("WORKFLOW_REF", "main")
    if not (GH_PAT and REPO_OWNER and REPO_NAME):
        st.sidebar.error("Set GH_PAT, REPO_OWNER, REPO_NAME in env (.env).")
    else:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"token {GH_PAT}",
        }
        payload = {"ref": REF}
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            if r.status_code in (204, 201):
                st.sidebar.success("Dispatch accepted. Check Actions tab for run.")
            else:
                st.sidebar.error(f"GitHub API returned {r.status_code}: {r.text}")
        except Exception as e:
            st.sidebar.error(f"Dispatch failed: {e}")

st.sidebar.markdown("---")

# --- Server-side newsletter regeneration ---
if st.sidebar.button("📄 Generate newsletter PDF (server)"):
    try:
        # run newsletter generator script on server (assumes python environment on host)
        subprocess.check_call([sys.executable, "app/newsletter_generator.py"])
        st.sidebar.success(f"Newsletter (PDF) regenerated at {PDF_PATH}")
    except Exception as e:
        st.sidebar.error(f"Failed to generate PDF: {e}")

st.sidebar.markdown("---")

# --- PDF download button (if available) ---
if os.path.exists(PDF_PATH):
    try:
        with open(PDF_PATH, "rb") as f:
            pdf_bytes = f.read()
        st.sidebar.download_button(
            label="⬇️ Download Newsletter (PDF)",
            data=pdf_bytes,
            file_name="arxiv_newsletter.pdf",
            mime="application/pdf",
        )
    except Exception as e:
        st.sidebar.error(f"Failed to load PDF for download: {e}")
else:
    st.sidebar.info("Newsletter PDF not found. Run GH pipeline or Generate newsletter PDF (server).")

st.sidebar.markdown("---")
st.sidebar.markdown("Env loaded from .env. Ensure GROQ_API_KEY set for LLM.")

# --- Main area ---
st.markdown(f"**Total processed papers:** {len(proc)}")

# Filters
categories = ["All"] + sorted(proc["category"].dropna().unique().tolist()) if not proc.empty else ["All"]
selected_category = st.selectbox("📂 Select Category", categories)
search = st.text_input("🔍 Search by title or author")

df_view = proc.copy()
if selected_category != "All":
    df_view = df_view[df_view["category"] == selected_category]
if search:
    df_view = df_view[
        df_view["title"].str.contains(search, case=False, na=False)
        | df_view["authors"].str.contains(search, case=False, na=False)
    ]

# show date of dataset generation (use latest summary_updated)
if not proc.empty and proc["summary_updated"].astype(bool).any():
    latest_ts = proc.loc[proc["summary_updated"].astype(bool), "summary_updated"].max()
    st.caption(f"Data last updated (latest summary_generated): {human_ts(latest_ts)} UTC")
else:
    st.caption("No summary_generated timestamps found yet.")

# Table display
if df_view.empty:
    st.info("No processed summaries found (or filtered out). You can generate summaries with the buttons below.")
else:
    df_view_display = df_view[["title", "authors", "category", "summary", "summary_updated", "week_of_update", "link"]].copy()
    df_view_display["summary_updated"] = df_view_display["summary_updated"].apply(human_ts)
    df_view_display = df_view_display.rename(columns={
        "summary": "LLM_summary",
        "summary_updated": "summary_generated_at",
        "week_of_update": "week_of_update",
    })
    st.dataframe(df_view_display, height=380)

st.markdown("---")
st.subheader("Papers (detail)")

# If processed empty but raw present, allow per-row LLM generation
if proc.empty and not raw.empty:
    st.warning("No processed summaries. Generate per paper or run the summarizer.")
    sample = raw.head(50)
    for idx, r in sample.iterrows():
        st.write(f"**{r['title']}**")
        cols = st.columns([5, 1])
        if cols[1].button("Generate summary", key=f"gen_raw_{idx}"):
            if not GROQ_API_KEY:
                st.error("GROQ_API_KEY not set in env.")
            else:
                try:
                    client = Groq(api_key=GROQ_API_KEY)
                    prompt = f"Summarize this research paper for a general audience.\n\nTitle: {r['title']}\n\nAbstract: {r.get('abstract','')}\n\nSummary:"
                    resp = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[{"role": "system", "content": "You are a concise summarizer."}, {"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=800,
                    )
                    summary = resp.choices[0].message.content.strip()
                except Exception as e:
                    summary = f"ERROR: {e}"
                ts = now_iso()
                wk = week_of_iso(ts)
                new_row = r.to_dict()
                new_row.update({"summary": summary, "summary_updated": ts, "week_of_update": wk})
                # append to processed CSV
                if os.path.exists(CSV_PATH):
                    df_proc = pd.read_csv(CSV_PATH)
                    df_proc = pd.concat([df_proc, pd.DataFrame([new_row])], ignore_index=True, sort=False)
                else:
                    df_proc = pd.DataFrame([new_row])
                df_proc.to_csv(CSV_PATH, index=False)
                st.experimental_rerun()

# If processed present, let user select and regenerate
if not proc.empty:
    sel_title = st.selectbox("Select paper to view / regenerate", options=proc["title"].tolist())
    row = proc[proc["title"] == sel_title].iloc[0]
    st.markdown(f"### {row['title']}")
    st.markdown(f"**Authors:** {row.get('authors','-')}  —  **Category:** {row.get('category','-')}")
    st.markdown(f"**Summary generated at:** {human_ts(row.get('summary_updated',''))} UTC")
    st.markdown(f"**Week:** {row.get('week_of_update','')}")
    st.markdown("#### LLM Summary")
    st.write(row.get("summary", "*No summary stored.*"))

    if st.button("Regenerate summary (LLM)"):
        if not GROQ_API_KEY:
            st.error("GROQ_API_KEY not set.")
        else:
            with st.spinner("Calling LLM to regenerate summary..."):
                try:
                    client = Groq(api_key=GROQ_API_KEY)
                    prompt = f"Summarize this research paper for a general audience.\n\nTitle: {row['title']}\n\nAbstract: {row.get('abstract','')}\n\nSummary:"
                    resp = client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=[{"role": "system", "content": "You are a concise summarizer."}, {"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=800,
                    )
                    summary = resp.choices[0].message.content.strip()
                except Exception as e:
                    summary = f"ERROR: {e}"
                ts = now_iso()
                wk = week_of_iso(ts)
                # update CSV on disk
                df_proc = pd.read_csv(CSV_PATH)
                mask = df_proc["title"] == row["title"]
                df_proc.loc[mask, "summary"] = summary
                df_proc.loc[mask, "summary_updated"] = ts
                df_proc.loc[mask, "week_of_update"] = wk
                df_proc.to_csv(CSV_PATH, index=False)
                st.success("Regenerated summary and saved to CSV.")
                st.experimental_rerun()
