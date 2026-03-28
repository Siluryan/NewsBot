from typing import Dict, List
from datetime import datetime
import re


def _count_keywords(text: str, keywords: List[str]) -> int:
    t = (text or "").lower()
    score = 0
    for kw in keywords:
        if kw in t:
            score += 1
        if re.search(rf"\b{re.escape(kw)}\b", t):
            score += 1
    return score


def _recency_bonus(published_at: str) -> float:
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        delta_days = (datetime.utcnow() - dt.replace(tzinfo=None)).days
        if delta_days <= 1:
            return 2.0
        if delta_days <= 3:
            return 1.0
        if delta_days <= 7:
            return 0.5
    except Exception:
        pass
    return 0.0


def score_item(item: Dict[str, str], include: List[str]) -> float:
    title = item.get("title", "")
    summary = item.get("summary", "")
    base = _count_keywords(title, include) * 2 + _count_keywords(summary, include)
    base += _recency_bonus(item.get("published_at", ""))
    return float(base)


def rank_items(items: List[Dict[str, str]], include: List[str]) -> List[Dict[str, str]]:
    for it in items:
        it["score"] = score_item(it, include)
    return sorted(items, key=lambda x: x.get("score", 0.0), reverse=True)
