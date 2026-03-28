from typing import List, Dict, Optional

MAX_LEN = 2800


def _truncate(text: str, max_len: int = MAX_LEN) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rstrip() + "..."


def build_post(items: List[Dict[str, str]]) -> Optional[str]:
    if not items:
        return None

    for it in items:
        if it.get("editorial"):
            return _truncate(it["editorial"])

    top = items[0]
    summary = (top.get("summary") or "").strip()
    title = top.get("title", "")
    url = top.get("url", "")

    if summary:
        text = f"{summary}\n\n{title}\n{url}"
    else:
        text = f"{title}\n{url}"

    return _truncate(text)
