import os
import re
import sys
from typing import List, Dict, Optional
from .llm_helper import chat

_OUTPUT_GUARDRAIL = (
    " A saída deve ser apenas o texto do post, pronto para publicar: "
    "sem preâmbulo, sem explicar o que vai fazer e sem repetir o pedido. "
    "Não repita a mesma ideia em parágrafos diferentes nem reformule o mesmo ponto "
    "só para alongar o texto. Cada parágrafo deve acrescentar algo novo. "
    "A primeira linha deve ser o gancho de abertura, sem URL nessa linha. "
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

    "ESTRUTURA: a primeira linha é um gancho — UMA afirmação curta, no máximo 90 caracteres, "
    "que expõe a tensão central do assunto e faz o leitor parar a rolagem. "
    "Afirmação seca, nunca pergunta, nunca manchete copiada, nunca frase publicitária. "
    "Português natural e gramaticalmente correto. Substantivo antes do adjunto, "
    "na ordem corrente da língua. Leia o gancho em voz alta: se travar, reescreva. "
    "O gancho precisa ser sustentado pelo resto do texto: se os parágrafos não provam o que "
    "ele afirma, troque o gancho. "
    "Não repita o título da notícia em lugar nenhum — o preview do link já mostra o título. "
    "Depois do gancho, uma linha em branco e no máximo 2 parágrafos curtos "
    "separados por linha em branco. Dois parágrafos, não três. "
    "Alvo de 650 a 900 caracteres no total, contando o gancho. "
    "Os dois parágrafos precisam sobreviver inteiros dentro desse alvo: "
    "é melhor cortar um argumento do que entregar um parágrafo unico e denso. "
    "Não siga um molde fixo de contexto, depois opinião, depois conclusão. "
    "Abra pelo detalhe mais concreto ou mais incômodo da notícia e desenvolva a partir dele. "
    "Se dois parágrafos podem trocar de lugar sem que o texto perca nada, "
    "um dos dois é supérfluo: corte e escreva só dois. "

    "TESE: o post defende uma posição, não descreve uma novidade. "
    "Diga o que a fonte acerta, o que ela superestima e o que ela deixa de fora. "
    "Discordar da fonte é permitido e desejável quando houver base para isso no próprio texto dela. "
    "A opinião é sobre engenharia: o que quebra, o que custa, o que essa abordagem assume "
    "que nem sempre é verdade, para quem ela não serve. "
    "Teste antes de entregar: se o texto poderia ter sido escrito pela empresa que publicou a "
    "notícia, ele não tem tese — refaça. "

    "TOM: escreva com a segurança de quem conhece o terreno, não como quem resume a notícia. "
    "Essa vivência aparece no julgamento sobre o que a fonte descreve — no que é acertado, "
    "arriscado, superestimado ou mal resolvido — e NUNCA em relato de caso próprio. "
    "Não narre incidentes, bugs, times, projetos ou correções que você teria vivido, "
    "nem escreva em primeira pessoa do plural operacional "
    "('quando implementamos', 'passamos a monitorar', 'na nossa infra', 'o efeito colateral foi'). "
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
    "Em especial, nada de advertência genérica no fecho, do tipo "
    "'quem ainda faz X está operando no escuro' ou 'ou você se adapta, ou fica para trás'. "
    "Não use bullets, listas, emojis, hashtags, negrito ou travessões decorativos. "

    "No final, após o último parágrafo, uma linha em branco e por último a URL da fonte sozinha nessa linha. "

    "FATOS — esta regra prevalece sobre todas as outras, inclusive sobre a exigência de tese "
    "e de gancho. Todo dado concreto precisa estar no texto da fonte: número, porcentagem, "
    "versão de software, sistema operacional, modelo de dispositivo, navegador, região, empresa, "
    "produto, incidente ou caso. Antes de escrever qualquer especificidade, localize-a na fonte; "
    "se não achar, não escreva. NUNCA invente estatística, métrica, benchmark, exemplo ou falha, "
    "nem relate como vivido algo que a fonte não descreve. "
    "Não combine dois dados separados da fonte numa única afirmação que ela não faz: "
    "se ela diz que 14% dos usuários abandonam o pagamento E, em outro ponto, que há churn "
    "numa região, NÃO escreva que 14% abandonam naquela região. Mantenha cada dado no "
    "contexto em que a fonte o apresenta. "
    "Se a fonte não traz números, argumente sem números: descreva o mecanismo técnico que ela "
    "apresenta e o que ele implica. Opinião, ressalva, crítica e projeção de risco são bem-vindas "
    "e não precisam estar na fonte, desde que soem como opinião e não como fato relatado. "
    "Um texto correto e sem números vale mais que um texto específico e inventado: "
    "a especificidade fabricada é o pior defeito possível neste post."
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


EDITORIAL_MAX_CHARS = int(os.getenv("EDITORIAL_MAX_CHARS") or 1300)


def _enforce_limit(text: str, max_chars: int = EDITORIAL_MAX_CHARS) -> str:
    """Garante o teto de caracteres sem cortar no meio da frase.

    Modelo de linguagem nao conta caractere de forma confiavel, entao pedir o
    limite no prompt nao basta. Remove paragrafos inteiros do fim ate caber,
    preservando sempre o gancho e ao menos um paragrafo.
    """
    if len(text) <= max_chars:
        return text
    blocos = [b for b in text.split("\n\n") if b.strip()]
    while len("\n\n".join(blocos)) > max_chars and len(blocos) > 1:
        atual = len("\n\n".join(blocos))
        frases = re.split(r"(?<=[.!?…])\s+", blocos[-1].strip())
        if len(frases) > 1:
            # Tira a ultima frase antes de sacrificar o paragrafo inteiro:
            # colapsar para um bloco unico vira parede de texto.
            blocos[-1] = " ".join(frases[:-1])
            print(
                f"[editorial] {atual} chars acima do teto de {max_chars} — "
                f"removida frase final ({len(frases[-1])} chars).",
                file=sys.stderr,
            )
        elif len(blocos) > 2:
            removido = blocos.pop()
            print(
                f"[editorial] {atual} chars acima do teto de {max_chars} — "
                f"removido paragrafo final ({len(removido)} chars).",
                file=sys.stderr,
            )
        else:
            break
    saida = "\n\n".join(blocos)
    if len(saida) > max_chars:
        print(
            f"[editorial] Ainda em {len(saida)} chars com o minimo de paragrafos; "
            f"mantido inteiro para nao cortar no meio da frase.",
            file=sys.stderr,
        )
    return saida


def generate_editorial(items: List[Dict[str, str]], max_tokens: int = 2000) -> Optional[str]:
    if not items:
        return None

    top = items[0]
    title   = top.get("title", "")
    url     = top.get("url", "")
    summary = (top.get("summary", "") or "")[:600]
    content = (top.get("content", "") or "")[:3500]
    fonte   = f"Título: {title}\nURL: {url}\nResumo: {summary}"
    if content:
        fonte += f"\n\nTexto do artigo (pode estar truncado):\n{content}"

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
    return _ensure_source_url_at_end(_enforce_limit(cleaned), url)
