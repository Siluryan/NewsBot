from typing import Optional
import re
import requests

USER_AGENT = "Mozilla/5.0 (compatible; NewsBot/1.0; +https://example.local)"


def get_og_image(url: str, timeout: int = 10) -> Optional[str]:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        resp.raise_for_status()
        html = resp.text
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if m:
            return m.group(1)
        m2 = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if m2:
            return m2.group(1)
    except Exception:
        return None
    return None
