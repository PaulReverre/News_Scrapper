# canada_news_notifier.py
# Windows Tkinter popup that shows top 3 Canadian news items (business/economy, politics, energy, BC)
# with emojis, short summaries, and clickable links. Stays open until you close it.

import tkinter as tk
from tkinter import ttk
import webbrowser
import time
import re
import html
from datetime import datetime
import feedparser

# ---------- CONFIG ----------
MAX_ITEMS = 3
SUMMARY_CHARS = 220  # target length for summary snippet

# Canadian RSS feeds focused on your topics
FEEDS = [
    # CBC
    "https://www.cbc.ca/cmlink/rss-business",
    "https://www.cbc.ca/cmlink/rss-politics",
    "https://www.cbc.ca/cmlink/rss-canada-britishcolumbia",
    # Global News
    "https://globalnews.ca/business/feed/",
    "https://globalnews.ca/politics/feed/",
    "https://globalnews.ca/bc/feed/",
    # Financial Post
    "https://financialpost.com/category/news/economy/feed/",
    "https://financialpost.com/category/news/energy/feed/",
    "https://financialpost.com/category/news/fp-street/feed/",
    # Vancouver Sun (BC provincial & local)
    "https://vancouversun.com/category/news/local-news/bc/feed/",
    "https://vancouversun.com/category/business/local-business/feed/",
]

# Topic tagging via keywords -> emoji + label
TOPIC_TAGS = [
    # (emoji, label, keywords)
    ("💼", "Business/Economy",
     ["economy", "economic", "gdp", "inflation", "interest rate", "bank of canada",
      "finance", "markets", "market", "stocks", "tsx", "investment", "business", "jobs", "unemployment"]),
    ("🗳", "Politics",
     ["politics", "parliament", "pm", "prime minister", "minister", "cabinet", "policy",
      "legislation", "election", "ottawa", "federal", "provincial government", "ndp", "liberal", "conservative"]),
    ("⚡", "Energy",
     ["energy", "oil", "gas", "lng", "pipeline", "trans mountain", "tmx", "hydro", "electricity",
      "renewable", "wind", "solar", "utility", "mining"]),
    ("🌲", "BC Provincial",
     ["british columbia", "b.c.", "bc", "vancouver", "victoria", "surrey", "burnaby", "kelowna",
      "translink", "bc hydro", "province", "provincial"])
]

# ---------- HELPERS ----------
def clean_text(t: str) -> str:
    if not t:
        return ""
    t = html.unescape(t)
    # remove HTML tags
    t = re.sub(r"<[^>]+>", "", t)
    # collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t

def summarize(text: str, limit=SUMMARY_CHARS) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    # try to cut at sentence boundary
    cut = text[:limit]
    last_period = cut.rfind(".")
    if last_period > int(limit * 0.6):  # reasonable sentence end
        return cut[:last_period + 1]
    return cut.rstrip() + "…"

def pick_topic(title: str, summary: str, source_hint: str = ""):
    base = f"{title} {summary} {source_hint}".lower()
    # Prefer BC if feed is clearly BC
    if any(tag in source_hint.lower() for tag in ["british columbia", "bc", "vancouver sun", "vancouversun", "global news bc", "cbc british columbia"]):
        return "🌲", "BC Provincial"
    for emoji, label, keywords in TOPIC_TAGS:
        if any(kw in base for kw in keywords):
            return emoji, label
    # default to business/economy if nothing hits (common for CA news)
    return "💼", "Business/Economy"

def entry_time(e):
    # Try published_parsed then updated_parsed
    tt = None
    if hasattr(e, "published_parsed") and e.published_parsed:
        tt = e.published_parsed
    elif hasattr(e, "updated_parsed") and e.updated_parsed:
        tt = e.updated_parsed
    else:
        return 0
    # convert to epoch
    try:
        return int(time.mktime(tt))
    except Exception:
        return 0

def dedupe(items):
    seen = set()
    uniq = []
    for it in items:
        key = (it.get("title","").strip().lower(), it.get("link","").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(it)
    return uniq

import requests

def collect_news():
    all_items = []
    for url in FEEDS:
        try:
            # Try to get feed XML with a short timeout
            resp = requests.get(url, timeout=3)  # 3-second limit
            if resp.status_code != 200 or not resp.text.strip():
                continue

            fp = feedparser.parse(resp.text)
            source_title = fp.feed.title if fp.feed and "title" in fp.feed else url

            for e in fp.entries[:20]:
                title = clean_text(getattr(e, "title", ""))
                link = getattr(e, "link", "")
                summary = summarize(getattr(e, "summary", "") or getattr(e, "description", ""))
                published = entry_time(e)
                emoji, topic = pick_topic(title, summary, source_hint=source_title)
                if not title or not link:
                    continue
                all_items.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "time": published,
                    "source": source_title,
                    "emoji": emoji,
                    "topic": topic
                })

        except requests.exceptions.Timeout:
            print(f"[Timeout] Skipping slow feed: {url}")
            continue
        except Exception as ex:
            print(f"[Error] {url}: {ex}")
            continue

    # Sort newest first, dedupe, and take top N
    all_items = dedupe(sorted(all_items, key=lambda x: x["time"], reverse=True))
    themed = [x for x in all_items if x["topic"] in {"Business/Economy", "Politics", "Energy", "BC Provincial"}]
    return themed[:MAX_ITEMS]

# ---------- UI ----------
def open_link(url):
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass

def build_ui(items):
    root = tk.Tk()
    root.title("🇨🇦 Top Canadian News")
    root.geometry("680x520")
    root.minsize(560, 420)
    root.attributes("-topmost", True)  # bring to front
    try:
        # On Windows, this hints the taskbar (optional)
        root.iconbitmap(default="")  # no embedded icon; safe no-op
    except Exception:
        pass

    # Colors and typography
    BG = "#0f172a"       # slate-900
    CARD = "#111827"     # gray-900
    ACCENT = "#38bdf8"   # sky-400
    TEXT = "#e5e7eb"     # gray-200
    MUTED = "#cbd5e1"    # slate-300
    HILITE = "#22c55e"   # green-500

    root.configure(bg=BG)

    # Title bar
    title_frame = tk.Frame(root, bg=BG)
    title_frame.pack(fill="x", padx=16, pady=(16, 8))

    title_label = tk.Label(
        title_frame,
        text="Top Canadian News (Business • Politics • Energy • BC)",
        font=("Segoe UI Semibold", 15),
        fg=TEXT, bg=BG
    )
    title_label.pack(side="left")

    time_label = tk.Label(
        title_frame,
        text=datetime.now().strftime("Updated %b %d, %Y — %I:%M %p"),
        font=("Segoe UI", 10),
        fg=MUTED, bg=BG
    )
    time_label.pack(side="right")

    # Container (card look)
    card = tk.Frame(root, bg=CARD, bd=0, highlightthickness=0)
    card.pack(fill="both", expand=True, padx=16, pady=8)

    # Scrollable area (in case summaries get long)
    canvas = tk.Canvas(card, bg=CARD, bd=0, highlightthickness=0)
    vsb = ttk.Scrollbar(card, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=CARD)

    # (inside your build_ui(...) function, right after creating canvas and inner frames)
    def on_mousewheel(event):
        # For Windows, wheel delta is in steps of 120
        delta = -1*(event.delta // 120)
        canvas.yview_scroll(delta, "units")

    # Bind the mouse wheel events
    canvas.bind_all("<MouseWheel>", on_mousewheel)  # Windows
    canvas.bind_all("<Button-4>", on_mousewheel)    # Linux scroll up
    canvas.bind_all("<Button-5>", on_mousewheel)    # Linux scroll down


    inner.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=vsb.set)

    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Render each item
    if not items:
        empty = tk.Label(inner, text="No recent stories found. Try again later.",
                         font=("Segoe UI", 12), fg=MUTED, bg=CARD, padx=12, pady=12)
        empty.pack(fill="x", pady=8)
    else:
        for i, it in enumerate(items, start=1):
            block = tk.Frame(inner, bg=CARD)
            block.pack(fill="x", padx=14, pady=10)

            # Topic chip with emoji
            topic_chip = tk.Label(
                block,
                text=f"{it['emoji']}  {it['topic']}",
                font=("Segoe UI Semibold", 10),
                fg=ACCENT, bg=CARD
            )
            topic_chip.pack(anchor="w")

            # Headline (clickable)
            headline = tk.Label(
                block,
                text=f"{it['title']}",
                font=("Segoe UI Semibold", 13),
                fg=TEXT, bg=CARD, wraplength=620, justify="left", cursor="hand2"
            )
            headline.pack(anchor="w", pady=(2, 2))
            headline.bind("<Button-1>", lambda e, url=it["link"]: open_link(url))

            # Summary
            summary = tk.Label(
                block,
                text=it["summary"] if it["summary"] else "No summary provided.",
                font=("Segoe UI", 11),
                fg=MUTED, bg=CARD, wraplength=620, justify="left"
            )
            summary.pack(anchor="w", pady=(0, 4))

            # Source + Read link
            bottom = tk.Frame(block, bg=CARD)
            bottom.pack(fill="x")

            src = tk.Label(
                bottom, text=f"Source: {it['source']}",
                font=("Segoe UI", 9), fg=MUTED, bg=CARD
            )
            src.pack(side="left")

            read_link = tk.Label(
                bottom, text="Read ↗", font=("Segoe UI Semibold", 10), fg=HILITE, bg=CARD, cursor="hand2"
            )
            read_link.pack(side="right")
            read_link.bind("<Button-1>", lambda e, url=it["link"]: open_link(url))

            # Separator line
            if i != len(items):
                sep = tk.Frame(inner, bg="#1f2937", height=1)  # gray-800
                sep.pack(fill="x", padx=8, pady=6)

    # Buttons
    btns = tk.Frame(root, bg=BG)
    btns.pack(fill="x", padx=16, pady=(8, 14))

    def refresh():
        for w in inner.winfo_children():
            w.destroy()
        new_items = collect_news()
        # Rebuild UI list
        if not new_items:
            empty = tk.Label(inner, text="No recent stories found. Try again later.",
                             font=("Segoe UI", 12), fg=MUTED, bg=CARD, padx=12, pady=12)
            empty.pack(fill="x", pady=8)
        else:
            for i, it in enumerate(new_items, start=1):
                block = tk.Frame(inner, bg=CARD)
                block.pack(fill="x", padx=14, pady=10)

                topic_chip = tk.Label(
                    block, text=f"{it['emoji']}  {it['topic']}",
                    font=("Segoe UI Semibold", 10), fg=ACCENT, bg=CARD
                )
                topic_chip.pack(anchor="w")

                headline = tk.Label(
                    block, text=f"{it['title']}",
                    font=("Segoe UI Semibold", 13), fg=TEXT, bg=CARD, wraplength=620, justify="left", cursor="hand2"
                )
                headline.pack(anchor="w", pady=(2, 2))
                headline.bind("<Button-1>", lambda e, url=it["link"]: open_link(url))

                summary = tk.Label(
                    block, text=it["summary"] if it["summary"] else "No summary provided.",
                    font=("Segoe UI", 11), fg=MUTED, bg=CARD, wraplength=620, justify="left"
                )
                summary.pack(anchor="w", pady=(0, 4))

                bottom = tk.Frame(block, bg=CARD)
                bottom.pack(fill="x")

                src = tk.Label(bottom, text=f"Source: {it['source']}",
                               font=("Segoe UI", 9), fg=MUTED, bg=CARD)
                src.pack(side="left")

                read_link = tk.Label(
                    bottom, text="Read ↗", font=("Segoe UI Semibold", 10), fg=HILITE, bg=CARD, cursor="hand2"
                )
                read_link.pack(side="right")
                read_link.bind("<Button-1>", lambda e, url=it["link"]: open_link(url))

                if i != len(new_items):
                    sep = tk.Frame(inner, bg="#1f2937", height=1)
                    sep.pack(fill="x", padx=8, pady=6)

        time_label.config(text=datetime.now().strftime("Updated %b %d, %Y — %I:%M %p"))

    refresh_btn = tk.Button(btns, text="Refresh Now", font=("Segoe UI", 10),
                            bg="#1f2937", fg=TEXT, activebackground="#1f2937", activeforeground=TEXT,
                            bd=0, padx=12, pady=6, command=refresh)
    refresh_btn.pack(side="left")

    close_btn = tk.Button(btns, text="Close", font=("Segoe UI", 10),
                          bg="#ef4444", fg="white", activebackground="#ef4444", activeforeground="white",
                          bd=0, padx=14, pady=6, command=root.destroy)
    close_btn.pack(side="right")

    root.mainloop()

def main():
    items = collect_news()
    build_ui(items)

if __name__ == "__main__":
    main()
