import os
import re
from typing import List, Dict, Optional
from .llm_helper import chat

_OUTPUT_GUARDRAIL = (
    " A saída deve ser apenas o texto do post, pronto para publicar: "
    "sem preâmbulo, sem explicar o que vai fazer e sem repetir o pedido. "
    "Não repita a mesma ideia em parágrafos diferentes nem reformule o mesmo ponto "
    "só para alongar o texto. Cada parágrafo deve acrescentar algo novo. "
    "A primeira linha deve ser só o título da notícia (sem URL nessa linha). "
    "A URL da fonte deve aparecer uma única vez, sozinha na última linha do texto, "
    "após uma linha em branco a partir do parágrafo final, sem nada depois dela."
)

_DEFAULT_PROMPT = (
    "Você é um engenheiro sênior com 15 anos de experiência em DevOps, SRE e Cloud. "
    "Escreva UM post opinativo curto para LinkedIn ESTRITAMENTE sobre "
    "DevOps, SRE, Cloud Computing, segurança de infraestrutura, arquitetura de sistemas "
    "ou boas práticas de engenharia. "
    "NUNCA escreva sobre Inteligência Artificial, Machine Learning, LLMs, dados ou ciência de dados — "
    "mesmo que a fonte mencione esses temas, foque apenas nos aspectos de "
    "infraestrutura, segurança, confiabilidade ou arquitetura envolvidos. "
    "Formato: primeira linha é só o título da notícia (sem link). "
    "Em seguida 2 a 3 parágrafos curtos separados por linha em branco: "
    "contexto do problema, opinião com trade-offs e, se couber em uma frase, "
    "um takeaway prático. Cada parágrafo traz UMA ideia distinta — "
    "não repita nem reformule o mesmo argumento para preencher espaço. "
    "Use entre 900 e 1300 caracteres no total. Prefira concisão a extensão. "
    "Não use bullets, listas, emojis nem hashtags. "
    "No final, após o último parágrafo, uma linha em branco e por último a URL da fonte sozinha nessa linha."
)

SYSTEM_PROMPT = (os.getenv("EDITORIAL_PROMPT") or _DEFAULT_PROMPT) + _OUTPUT_GUARDRAIL

_META_FIRST_LINE = re.compile(
    r"""(?ix)^
    (?:
        (?:gere|gerar|crie|criar|escreva|escrever|elabore|redija|faça)\b
      | aqui\s+(?:está|temos|vai)
      | segue(?:\s+(?:abaixo|o\s+post))?
      | (?:com|de)\s+base\s+(?:na|em)\s+(?:fonte|informa)
      | (?:a|na)\s+partir\s+d(?:esta|este|a|o)\s+fonte
      | (?:de\s+)?acordo\s+com\s+(?:as\s+)?(?:instru|orienta|solicit)
      | (?:conforme|como)\s+(?:solicitado|pedido|solicita)
      | (?:segue|abaixo)\s+o\s+post
      | post\s+(?:para|no)\s+linkedin
    )
    """,
)


def _strip_leading_meta_lines(text: str) -> str:
    lines = text.splitlines()
    while lines:
        raw = lines[0]
        s = raw.strip()
        if not s:
            lines.pop(0)
            continue
        if _META_FIRST_LINE.search(s) or (
            "fonte fornecida" in s.lower() and "post" in s.lower()
        ):
            lines.pop(0)
            continue
        break
    return "\n".join(lines).strip()


def _ensure_source_url_at_end(text: str, url: str) -> str:
    u = url.strip()
    if not u or not (u.startswith("http://") or u.startswith("https://")):
        return text
    esc = re.escape(u)
    lines = [ln for ln in text.splitlines() if ln.strip() != u]
    if lines:
        lines[0] = re.sub(r"^\s*t[íi]tulo\s*:\s*", "", lines[0], flags=re.IGNORECASE).strip()
        lines[0] = re.sub(rf"\s*[—–-]\s*{esc}\s*$", "", lines[0]).rstrip()
    body = "\n".join(lines).strip()
    if not body:
        return u
    return f"{body}\n\n{u}"


def generate_editorial(items: List[Dict[str, str]], max_tokens: int = 900) -> Optional[str]:
    if not items:
        return None

    top = items[0]
    title   = top.get("title", "")
    url     = top.get("url", "")
    summary = (top.get("summary", "") or "")[:600]
    fonte   = f"Título: {title}\nURL: {url}\nResumo: {summary}"

    raw = chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": fonte},
        ],
        temperature=0.7,
        max_tokens=max_tokens,
    )
    if not raw:
        return None
    cleaned = _strip_leading_meta_lines(raw)
    if not cleaned:
        return None
    return _ensure_source_url_at_end(cleaned, url)
