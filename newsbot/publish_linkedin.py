import os
import sys
import requests
from typing import Any, Dict, Optional


def _get_author_urn(access_token: str) -> str:
    env_urn = os.environ.get("LINKEDIN_MEMBER_URN", "").strip()
    if env_urn:
        return env_urn

    try:
        me = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if me.ok:
            sub = me.json().get("sub", "")
            if sub:
                return f"urn:li:person:{sub}"
    except Exception:
        pass

    print("Nao foi possivel resolver o author URN.", file=sys.stderr)
    sys.exit(1)


def _primary_article_url(explicit: Optional[str]) -> Optional[str]:
    raw = (explicit or os.environ.get("PRIMARY_LINK_URL") or "").strip()
    if not raw:
        return None
    lower = raw.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return raw
    return None


def post_text(text: str, article_url: Optional[str] = None) -> Dict:
    access_token = os.environ["LINKEDIN_ACCESS_TOKEN"]
    author = _get_author_urn(access_token)
    print(f"Postando como: {author}")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    url_for_preview = _primary_article_url(article_url)
    share_inner: Dict[str, Any] = {
        "shareCommentary": {
            "text": text,
        },
    }
    if url_for_preview:
        share_inner["shareMediaCategory"] = "ARTICLE"
        share_inner["media"] = [
            {
                "status": "READY",
                "originalUrl": url_for_preview,
            }
        ]
    else:
        share_inner["shareMediaCategory"] = "NONE"

    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": share_inner,
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
        },
    }

    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if not resp.ok:
        print(f"Erro {resp.status_code}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()

    return resp.json() if resp.text else {"status": resp.status_code}
