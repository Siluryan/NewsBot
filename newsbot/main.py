import os
from typing import List, Dict

from .collector import collect, save, load_sources
from .extract import extract_readable_text
from .summarize import summarize_text
from .ranker import rank_items
from .format_post import build_post
from .publish_linkedin import post_text
from .editorial import generate_editorial

TOP_N = 3


def run():
    items, conn = collect()
    if not items:
        print("Nenhum item novo relevante.")
        return

    cfg = load_sources()
    include = [k.lower() for k in cfg["keywords"]["include"]]
    ranked_titles = rank_items(items, include)

    enriched: List[Dict[str, str]] = []
    for it in ranked_titles[:TOP_N]:
        content = extract_readable_text(it["url"])
        summary = summarize_text(it["title"], it["url"], content)
        if summary:
            it["summary"] = summary
        enriched.append(it)

    ranked = rank_items(enriched, include)

    editorial = generate_editorial(ranked[:TOP_N])
    if editorial:
        ranked[0]["editorial"] = editorial

    text = build_post(ranked)
    if not text:
        print("Nada para postar.")
        return

    if os.getenv("DRY_RUN") == "1":
        print("=== DRY RUN: Conteudo do post ===")
        print(text)
    else:
        os.environ["PRIMARY_LINK_URL"] = ranked[0].get("url", "")
        res = post_text(text)
        save(items, conn)
        print("Publicado:", res)


if __name__ == "__main__":
    run()
