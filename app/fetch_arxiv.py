# app/fetch_arxiv.py
import feedparser
import pandas as pd
import os
import sys
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding='utf-8')

# --- Categories to fetch ---
CATEGORIES = [
    "cs.LG",  # Machine Learning
    "cs.CV",  # Computer Vision
    "cs.AI",  # Artificial Intelligence
    "cs.CL",  # Computation and Language (NLP)
    "stat.ML" # Statistics - Machine Learning
]

# --- Total papers target ---
TOTAL_PAPERS = 100
PAPERS_PER_CATEGORY = TOTAL_PAPERS // len(CATEGORIES)  # 20 each

def week_of_iso(iso_ts):
    try:
        dt = pd.to_datetime(iso_ts)
        monday = dt - pd.Timedelta(days=dt.dayofweek)
        return f"Week of {monday.date().isoformat()}"
    except Exception:
        return ""

def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()

def fetch_papers(category="cs.AI", max_results=20):
    """Fetch papers from a single ArXiv category."""
    url = f"http://export.arxiv.org/api/query?search_query=cat:{category}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    feed = feedparser.parse(url)

    papers = []
    fetched_at = now_iso()
    fetched_week = week_of_iso(fetched_at)

    for entry in feed.entries:
        # entry.summary is the abstract text from arXiv
        papers.append({
            "category": category,
            "title": entry.title.strip().replace("\n", " "),
            "summary": entry.summary.strip().replace("\n", " "),  # abstract
            "link": entry.link,
            "published": entry.published,
            "authors": ", ".join(a.name for a in entry.authors) if hasattr(entry, "authors") else "",
            # Added fetching metadata:
            "fetched_at": fetched_at,
            "fetched_week": fetched_week
        })
    return papers

def fetch_all_categories(categories=CATEGORIES, per_category=PAPERS_PER_CATEGORY):
    """Fetch papers from all categories and save to CSV."""
    os.makedirs("data/raw", exist_ok=True)
    all_papers = []

    for cat in categories:
        print(f"🔍 Fetching {per_category} latest papers from {cat}...")
        papers = fetch_papers(cat, max_results=per_category)
        print(f"  → Retrieved {len(papers)} papers from {cat}")
        all_papers.extend(papers)

    df = pd.DataFrame(all_papers)
    # ensure deterministic column order (optional)
    cols = ["category", "title", "authors", "link", "published", "summary", "fetched_at", "fetched_week"]
    existing = [c for c in cols if c in df.columns] + [c for c in df.columns if c not in cols]
    df = df.reindex(columns=existing)
    df.to_csv("data/raw/papers.csv", index=False)
    print(f"\n✅ Saved {len(df)} total papers to data/raw/papers.csv")

    return df

# --- MAIN ---
if __name__ == "__main__":
    fetch_all_categories()
