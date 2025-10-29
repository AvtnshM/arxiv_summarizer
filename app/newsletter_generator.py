# app/newsletter_generator.py

import pandas as pd
import os

# --- Load and clean data ---
df = pd.read_csv("data/processed/summarized.csv")

df["summary_short"] = df["summary_short"].fillna("").astype(str).str.strip()
df["summary_short"] = df["summary_short"].str.replace(
    r"^Here’s a summary of the research paper for a general audience[:\-]*\s*", "",
    regex=True
)
df["category"] = df["category"].fillna("Uncategorized")

# --- Create output directory ---
os.makedirs("output", exist_ok=True)

# --- Build HTML ---
categories = sorted(df["category"].unique().tolist())

html_content = f"""
<html>
<head>
    <title>AI Research Newspaper</title>
    <style>
        body {{
            font-family: 'Georgia', serif;
            background-color: #f7f7f7;
            color: #222;
            margin: 0;
            padding: 0;
        }}
        header {{
            background-color: #1a73e8;
            color: white;
            text-align: center;
            padding: 45px 25px;
            font-size: 2.3em;
            font-weight: bold;
            letter-spacing: 0.5px;
        }}
        .container {{
            width: 85%;
            margin: 30px auto;
            max-width: 1200px;
        }}
        .filter {{
            text-align: center;
            margin-bottom: 25px;
        }}
        select {{
            font-size: 16px;
            padding: 8px 14px;
            border-radius: 8px;
            border: 1px solid #aaa;
        }}
        .grid {{
            column-count: 2;
            column-gap: 40px;
        }}
        .paper {{
            background-color: #fff;
            display: inline-block;
            margin: 0 0 25px;
            width: 100%;
            border-radius: 10px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            padding: 20px;
            border-left: 6px solid #1a73e8;
        }}
        .paper h2 {{
            margin: 0 0 8px 0;
            font-size: 1.3em;
        }}
        .paper h2 a {{
            color: #1a5276;
            text-decoration: none;
        }}
        .paper h2 a:hover {{
            text-decoration: underline;
        }}
        .meta {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
        }}
        .paper p {{
            font-size: 0.95em;
            text-align: justify;
            line-height: 1.5;
        }}
        footer {{
            text-align: center;
            color: #555;
            font-size: 0.9em;
            padding: 20px 0;
            margin-top: 40px;
            border-top: 1px solid #ddd;
        }}
        @media (max-width: 800px) {{
            .grid {{
                column-count: 1;
            }}
        }}
    </style>
</head>
<body>
    <header>📰 AI Research Highlights – Weekly Edition</header>
    <div class="container">
        <div class="filter">
            <label for="categorySelect"><b>Filter by Category:</b></label>
            <select id="categorySelect" onchange="filterCategory()">
                <option value="All">All</option>
"""

# Dropdown options
for cat in categories:
    html_content += f'                <option value="{cat}">{cat}</option>\n'

html_content += """            </select>
        </div>
        <div class="grid">
"""

# Paper blocks
for _, row in df.iterrows():
    html_content += f"""
            <div class='paper' data-category='{row['category']}'>
                <h2><a href='{row['link']}' target='_blank'>{row['title']}</a></h2>
                <div class='meta'>{row['category']} | {row['authors']}</div>
                <p>{row['summary_short']}</p>
            </div>
    """

# Footer + JS
html_content += """
        </div>
    </div>
    <footer>Generated automatically by ArXiv Summarizer · © 2025</footer>

    <script>
        function filterCategory() {
            const selected = document.getElementById('categorySelect').value;
            const papers = document.getElementsByClassName('paper');
            for (let i = 0; i < papers.length; i++) {
                const category = papers[i].getAttribute('data-category');
                if (selected === 'All' || category === selected) {
                    papers[i].style.display = 'inline-block';
                } else {
                    papers[i].style.display = 'none';
                }
            }
        }
    </script>
</body>
</html>
"""

# --- Save output ---
with open("output/newsletter.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ Newsletter generated: output/newsletter.html (newspaper-style, interactive)")
