import feedparser
import pandas as pd
import os

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

def fetch_papers(category="cs.AI", max_results=20):
    """Fetch papers from a single ArXiv category."""
    url = f"http://export.arxiv.org/api/query?search_query=cat:{category}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    feed = feedparser.parse(url)

    papers = []
    for entry in feed.entries:
        papers.append({
            "category": category,
            "title": entry.title.strip().replace("\n", " "),
            "summary": entry.summary.strip().replace("\n", " "),
            "link": entry.link,
            "published": entry.published,
            "authors": ", ".join(a.name for a in entry.authors)
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
    df.to_csv("data/raw/papers.csv", index=False)
    print(f"\n✅ Saved {len(df)} total papers to data/raw/papers.csv")

    return df

# --- MAIN ---
if __name__ == "__main__":
    fetch_all_categories()
