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
    "Você é um engenheiro sênior com 15 anos de estrada em DevOps, SRE e Cloud. "
    "Escreva UM post opinativo curto para LinkedIn ESTRITAMENTE sobre "
    "DevOps, SRE, Cloud Computing, segurança de infraestrutura, arquitetura de sistemas "
    "ou boas práticas de engenharia. "
    "NUNCA escreva sobre Inteligência Artificial, Machine Learning, LLMs, dados ou ciência de dados — "
    "mesmo que a fonte mencione esses temas, foque apenas nos aspectos de "
    "infraestrutura, segurança, confiabilidade ou arquitetura envolvidos. "

    "ESTRUTURA: a primeira linha é só o título da notícia, sem link. "
    "Depois, 2 ou 3 parágrafos curtos separados por linha em branco, "
    "entre 900 e 1300 caracteres no total. "
    "Não siga um molde fixo de contexto, depois opinião, depois conclusão. "
    "Abra pelo detalhe mais concreto ou mais incômodo da notícia e desenvolva a partir dele. "
    "Se dois parágrafos podem trocar de lugar sem que o texto perca nada, "
    "um dos dois é supérfluo: corte e escreva só dois. "

    "TOM: escreva como quem já operou aquilo na prática, não como quem está resumindo a notícia. "
    "Assuma uma posição clara em vez de equilibrar os dois lados até sobrar neutralidade. "
    "Prefira o específico ao abstrato: cite o mecanismo, o modo de falha, a ferramenta ou o número "
    "em vez de falar em desafios, impactos, importância ou relevância. "
    "Varie o comprimento das frases. Evite simetria de manual. "

    "NÃO USE, em nenhuma variação: 'takeaway', 'a lição que fica', 'o ponto aqui é', "
    "'no fim das contas', 'vale lembrar', 'não à toa', 'a verdade é que', 'a grande sacada', "
    "'cada vez mais', 'nunca foi tão', 'mais do que nunca', 'em um mundo onde', "
    "'não se trata apenas de X, mas de Y'. "
    "Não abra com pergunta retórica. "
    "Não encerre com frase de efeito, moral da história nem convite para comentar — "
    "termine no último argumento e pare. "
    "Não use bullets, listas, emojis, hashtags, negrito ou travessões decorativos. "

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


def generate_editorial(items: List[Dict[str, str]], max_tokens: int = 2000) -> Optional[str]:
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
        temperature=0.85,
        max_tokens=max_tokens,
    )
    if not raw:
        return None
    cleaned = _strip_leading_meta_lines(raw)
    if not cleaned:
        return None
    return _ensure_source_url_at_end(cleaned, url)
