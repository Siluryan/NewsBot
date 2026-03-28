import os
from typing import List, Dict, Optional
from .llm_helper import chat

_DEFAULT_PROMPT = (
    "Você é um engenheiro sênior com 15 anos de experiência em DevOps, SRE e Cloud. "
    "Escreva UM post opinativo para LinkedIn ESTRITAMENTE sobre "
    "DevOps, SRE, Cloud Computing, segurança de infraestrutura, arquitetura de sistemas "
    "ou boas práticas de engenharia. "
    "NUNCA escreva sobre Inteligência Artificial, Machine Learning, LLMs, dados ou ciência de dados — "
    "mesmo que a fonte mencione esses temas, foque apenas nos aspectos de "
    "infraestrutura, segurança, confiabilidade ou arquitetura envolvidos. "
    "Formato: primeira linha é o título da notícia seguido de '—' e a URL. "
    "Depois 4 a 5 parágrafos densos separados por linha em branco, com "
    "tom humano e direto, contexto do problema real, opinião clara com trade‑offs e "
    "um takeaway prático que o leitor pode aplicar imediatamente. "
    "Use entre 1800 e 2500 caracteres no total. Não use bullets, listas, emojis nem hashtags."
)

SYSTEM_PROMPT = os.getenv("EDITORIAL_PROMPT") or _DEFAULT_PROMPT


def generate_editorial(items: List[Dict[str, str]], max_tokens: int = 900) -> Optional[str]:
    if not items:
        return None

    top = items[0]
    title   = top.get("title", "")
    url     = top.get("url", "")
    summary = (top.get("summary", "") or "")[:600]
    fonte   = f"Título: {title}\nURL: {url}\nResumo: {summary}"

    return chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Gere o post a partir desta fonte:\n\n{fonte}"},
        ],
        temperature=0.9,
        max_tokens=max_tokens,
    )
