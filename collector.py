import feedparser
import hashlib
import sqlite3
from datetime import datetime, timezone
import yaml
import re
from typing import List, Tuple, Dict, Any

DB_PATH = "newsbot/db.sqlite"
SOURCES_PATH = "newsbot/sources.yml"


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY,
        url TEXT,
        title TEXT,
        published_at TEXT
    );
    """)
    conn.commit()
    return conn


def load_sources() -> Dict[str, Any]:
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def matches_keywords(title: str, include: List[str], exclude: List[str]) -> bool:
    t = normalize(title)
    if any(x in t for x in exclude):
        return False
    return any(x in t for x in include)


def hash_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def collect() -> Tuple[List[Dict[str, str]], sqlite3.Connection]:
    cfg = load_sources()
    include = [k.lower() for k in cfg["keywords"]["include"]]
    exclude = [k.lower() for k in cfg["keywords"]["exclude"]]
    conn = init_db()
    cur = conn.cursor()

    picked: List[Dict[str, str]] = []
    for feed in cfg["feeds"]:
        parsed = feedparser.parse(feed["url"])
        for entry in parsed.entries[:20]:
            url = entry.get("link") or ""
            title = entry.get("title") or ""
            if not url or not title:
                continue
            if not matches_keywords(title, include, exclude):
                continue
            item_id = hash_id(url)
            cur.execute("SELECT 1 FROM items WHERE id = ?", (item_id,))
            if cur.fetchone():
                continue
            published = entry.get("published") or entry.get("updated") or datetime.now(timezone.utc).isoformat()
            picked.append({"id": item_id, "url": url, "title": title, "published_at": str(published)})

    seen_urls = set()
    unique: List[Dict[str, str]] = []
    for it in picked:
        if it["url"] in seen_urls:
            continue
        seen_urls.add(it["url"])
        unique.append(it)

    return unique, conn


def save(items: List[Dict[str, str]], conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    for it in items:
        cur.execute(
            "INSERT OR IGNORE INTO items (id, url, title, published_at) VALUES (?, ?, ?, ?)",
            (it["id"], it["url"], it["title"], it["published_at"]),
        )
    conn.commit()
