"""
Generate PDF newsletter only (output/newsletter.pdf) from data/processed/summarized.csv.
Uses WeasyPrint when available (preferred). Falls back to reportlab (text-only).
"""
import os
import pandas as pd
from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')

CSV_PATH = "data/processed/summarized.csv"
OUT_DIR = "output"
PDF_PATH = os.path.join(OUT_DIR, "newsletter.pdf")
os.makedirs(OUT_DIR, exist_ok=True)

if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"{CSV_PATH} not found. Run summarizer first.")

df = pd.read_csv(CSV_PATH)

# prefer full summary
df["summary"] = df.get("summary", df.get("summary_short", "")).fillna("").astype(str)
df["summary_updated"] = df.get("summary_updated", "").fillna("")
df["week_of_update"] = df.get("week_of_update", "").fillna("")

# compute newsletter headline week
if df["week_of_update"].astype(bool).any():
    newsletter_week = df["week_of_update"].mode().iloc[0]
else:
    newsletter_week = f"Week of {datetime.utcnow().date().isoformat()}"

# FIX: no 'published' column in processed CSV → sort by update time
df["_ts"] = pd.to_datetime(df["summary_updated"], errors="coerce")
df = df.sort_values("_ts", ascending=False).drop(columns=["_ts"], errors="ignore")

# build HTML
html = []
html.append(f"<h1>ArXiv Paper Summaries — {newsletter_week}</h1>")
html.append(f"<p>Generated: {datetime.utcnow().isoformat()} UTC</p>")
html.append("<hr/>")

for _, r in df.iterrows():
    html.append(f"<h2>{r['title']}</h2>")
    html.append(
        f"<div><strong>Authors:</strong> {r.get('authors','-')} &nbsp; "
        f"<strong>Updated:</strong> {r.get('summary_updated','-')}</div>"
    )
    html.append(f"<p>{r['summary']}</p>")
    html.append("<hr/>")

html_content = """
<html>
<head>
<meta charset='utf-8'>
<style>
body{font-family:Arial,Helvetica,sans-serif;padding:28px;}
h1{font-size:22px;}
h2{font-size:15px;margin-top:20px;}
p{font-size:12px;line-height:1.45}
</style>
</head>
<body>
""" + "\n".join(html) + "</body></html>"

# Try WeasyPrint
try:
    from weasyprint import HTML
    HTML(string=html_content).write_pdf(PDF_PATH)
    print(f"✅ PDF generated at {PDF_PATH} (WeasyPrint)")
    sys.exit(0)
except Exception as e:
    print("⚠️ WeasyPrint not available or failed:", e)
    print("Falling back to text-only PDF (reportlab)")

# Fallback: reportlab
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    c = canvas.Canvas(PDF_PATH, pagesize=letter)
    w, h = letter
    y = h - 72

    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, f"ArXiv Paper Summaries — {newsletter_week}")
    y -= 20

    c.setFont("Helvetica", 9)
    c.drawString(72, y, f"Generated: {datetime.utcnow().isoformat()} UTC")
    y -= 20

    for _, r in df.iterrows():
        if y < 100:
            c.showPage()
            y = h - 72

        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, y, r['title'][:150])
        y -= 14

        c.setFont("Helvetica", 9)
        authors_line = f"Authors: {r.get('authors','-')} | Updated: {r.get('summary_updated','-')}"
        c.drawString(72, y, authors_line[:1000])
        y -= 12

        summary = r.get("summary", "")[:4000]
        for i in range(0, len(summary), 110):
            if y < 72:
                c.showPage()
                y = h - 72
            c.drawString(72, y, summary[i:i+110])
            y -= 12
        y -= 12

    c.save()
    print(f"✅ Text-only PDF generated at {PDF_PATH} (reportlab fallback)")

except Exception as ex:
    print("❌ Fallback PDF generation failed:", ex)
    raise
