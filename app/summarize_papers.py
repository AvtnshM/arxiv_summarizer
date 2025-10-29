from groq import Groq
from dotenv import load_dotenv
import os
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Load environment variables ---
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

# --- Initialize Groq client ---
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- Model configuration ---
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"

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

    # Skip already summarized papers
    if "summary_short" in df.columns:
        mask = df["summary_short"].isna() | (df["summary_short"] == "")
        df_to_process = df[mask]
        print(f"Resuming summarization — {len(df_to_process)} papers remaining...")
    else:
        df["summary_short"] = ""
        df_to_process = df

    total = len(df_to_process)
    print(f"Starting summarization for {total} papers with {concurrent_requests} threads...")

    for i in range(0, total, batch_size):
        batch = df_to_process.iloc[i:i + batch_size]
        print(f"\n📚 Processing batch {i // batch_size + 1} ({len(batch)} papers)...")

        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = {
                executor.submit(summarize_paper, row["title"], row["summary"]): idx
                for idx, row in batch.iterrows()
            }

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    df.loc[idx, "summary_short"] = future.result()
                except Exception as e:
                    print(f"⚠️ Thread error at index {idx}: {e}")
                    df.loc[idx, "summary_short"] = "Error generating summary."

        # Save progress
        df.to_csv("data/processed/summarized.csv", index=False)
        print(f"✅ Batch {i // batch_size + 1} complete and saved.")
        
        # Respect rate limit (≈30 API calls/min)
        print("⏳ Cooling down for 20 seconds to respect rate limits...")
        time.sleep(20)

    print(f"\n✅ Done. {len(df)} papers summarized and saved to data/processed/summarized.csv")
    return df

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    summarize_all(concurrent_requests=5, batch_size=10, limit=100)
