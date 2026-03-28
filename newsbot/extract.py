from typing import Optional
import trafilatura


def extract_readable_text(url: str) -> Optional[str]:
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(
            downloaded,
            include_links=False,
            include_images=False,
            favor_precision=True,
        )
        if not text:
            return None
        cleaned = text.strip()
        return cleaned or None
    except Exception:
        return None
