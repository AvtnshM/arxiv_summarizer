from groq import Groq
from dotenv import load_dotenv
import os
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import sys
sys.stdout.reconfigure(encoding='utf-8')

# --- Load environment variables ---
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

# --- Initialize Groq client ---
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- Model configuration ---
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"

# --------- NEW UTIL FUNCTIONS ----------
def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()

def week_of_iso(ts):
    dt = pd.to_datetime(ts)
    monday = dt - pd.Timedelta(days=dt.dayofweek)
    return f"Week of {monday.date().isoformat()}"
# ---------------------------------------

# --- Summarize one paper ---
def summarize_paper(title, abstract):
    if not abstract.strip():
        return "No abstract available to summarize."

    prompt = f"Summarize this research paper for a general audience:\n\nTitle: {title}\n\nAbstract: {abstract}\n\nSummary:"

    try:
        response = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a scientific summarizer for newsletters."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Error summarizing '{title}': {e}")
        return "Error generating summary."

# --- Batch Summarization ---
def summarize_all(concurrent_requests=5, batch_size=10, limit=100):
    os.makedirs("data/processed", exist_ok=True)
    df = pd.read_csv("data/raw/papers.csv").head(limit)

    # ADD THESE COLUMNS IF MISSING
    if "summary_short" not in df.columns:
        df["summary_short"] = ""
    if "summary_updated" not in df.columns:
        df["summary_updated"] = ""
    if "week_of_update" not in df.columns:
        df["week_of_update"] = ""

    # Only summarize missing papers
    mask = df["summary_short"].isna() | (df["summary_short"] == "")
    df_to_process = df[mask]

    print(f"Resuming summarization — {len(df_to_process)} papers remaining...")
    total = len(df_to_process)

    print(f"Starting summarization for {total} papers with {concurrent_requests} threads...")

    for i in range(0, total, batch_size):
        batch = df_to_process.iloc[i:i + batch_size]
        print(f"\n📚 Processing batch {i // batch_size + 1} ({len(batch)} papers)...")

        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = {
                # FIXED: use abstract instead of row["summary"]
                executor.submit(summarize_paper, row["title"], row["summary"]): idx
                for idx, row in batch.iterrows()
            }

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    summary_text = future.result()
                    df.loc[idx, "summary_short"] = summary_text
                    df.loc[idx, "summary"] = summary_text

                    # NEW: write timestamp + week
                    ts = now_iso()
                    df.loc[idx, "summary_updated"] = ts
                    df.loc[idx, "week_of_update"] = week_of_iso(ts)

                except Exception as e:
                    print(f"⚠️ Thread error at index {idx}: {e}")
                    df.loc[idx, "summary_short"] = "Error generating summary."

        # Save after each batch
        df.to_csv("data/processed/summarized.csv", index=False)
        print(f"✅ Batch {i // batch_size + 1} complete and saved.")

        # Cooldown
        print("⏳ Cooling down for 20 seconds to respect rate limits...")
        time.sleep(20)

    print(f"\n✅ Done. {len(df)} papers summarized and saved to data/processed/summarized.csv")
    return df

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    summarize_all(concurrent_requests=5, batch_size=10, limit=100)
