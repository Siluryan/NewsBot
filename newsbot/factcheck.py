"""Verificacao das afirmacoes do post contra o texto da fonte.

O editorial e gerado a temperature alta para nao soar formulaico, o que
traz variacao: entre as execucoes validadas na branch, metade produziu
alguma afirmacao sem respaldo — numero inventado, versao de sistema que
a fonte nao cita, ou dois dados verdadeiros fundidos numa afirmacao que
ela nao faz. Como o post sai no nome de uma pessoa, a checagem roda
antes de publicar.
"""

import os
import sys
from typing import List, Optional

from .llm_helper import chat

_DEFAULT_PROMPT = (
    "Você é um verificador de fatos rigoroso. Recebe o TEXTO DA FONTE e um POST "
    "escrito a partir dela. Sua tarefa é listar as afirmações do post que NÃO têm "
    "respaldo no texto da fonte.\n\n"

    "SINALIZE:\n"
    "- número, porcentagem, data, versão de software, sistema operacional, modelo de "
    "dispositivo, navegador, região, empresa ou produto que não apareça na fonte;\n"
    "- incidente, caso, benchmark ou exemplo que a fonte não descreva;\n"
    "- experiência relatada como vivida pelo autor que a fonte não mencione;\n"
    "- conflação: dois dados que existem na fonte separadamente, combinados numa "
    "afirmação que ela não faz. Exemplo: a fonte diz que 14% dos usuários abandonam o "
    "pagamento e, em outro ponto, que há churn numa região; o post afirmar que 14% "
    "abandonam naquela região é conflação e deve ser sinalizada;\n"
    "- atribuição à fonte de uma conclusão que ela não tira.\n\n"

    "NÃO SINALIZE:\n"
    "- opinião, juízo de valor, crítica ou discordância em relação à fonte;\n"
    "- projeção de risco e ressalva ('pode gerar', 'exige cuidado', 'sem isso, vira');\n"
    "- afirmação sobre o que a fonte deixa de fazer ou não detalha, quando for verdade;\n"
    "- reformulação fiel do conteúdo da fonte em outras palavras;\n"
    "- conhecimento técnico geral e incontroverso da área;\n"
    "- a URL no final do post.\n\n"

    "SAÍDA: se nenhuma afirmação for problemática, responda exatamente OK e nada mais. "
    "Caso contrário, liste uma afirmação por linha, cada linha começando com '- ', "
    "citando o trecho do post e dizendo em poucas palavras por que não tem respaldo. "
    "Sem preâmbulo, sem conclusão, sem numeração."
)

SYSTEM_PROMPT = os.getenv("FACTCHECK_PROMPT") or _DEFAULT_PROMPT


def unsupported_claims(
    post: str,
    source_text: str,
    max_tokens: int = 1500,
) -> Optional[List[str]]:
    """Afirmacoes do post sem respaldo na fonte.

    Lista vazia significa post aprovado. None significa que a verificacao nao
    pode ser feita (nenhum provedor de LLM disponivel), caso em que cabe ao
    chamador decidir se publica assim mesmo.
    """
    if not post or not source_text:
        return None

    resposta = chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"TEXTO DA FONTE:\n{source_text}\n\n"
                f"POST A VERIFICAR:\n{post}"
            )},
        ],
        temperature=0.0,
        max_tokens=max_tokens,
        reasoning_effort="medium",
    )
    if resposta is None:
        return None

    limpo = resposta.strip()
    if limpo.upper().startswith("OK"):
        return []

    problemas = [
        linha.strip().lstrip("-").strip()
        for linha in limpo.splitlines()
        if linha.strip().startswith("-")
    ]
    if not problemas and limpo:
        # Modelo respondeu em prosa em vez da lista pedida. Nao da para saber se
        # aprovou; trata como indisponivel em vez de aprovar por engano.
        print(
            "[factcheck] Resposta fora do formato esperado — verificacao inconclusiva.",
            file=sys.stderr,
        )
        return None
    return problemas
