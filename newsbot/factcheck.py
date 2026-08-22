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
    "Você é um verificador de fatos. Recebe o TEXTO DA FONTE e um POST escrito a "
    "partir dela. O post é opinativo por natureza: ele interpreta, critica e projeta "
    "riscos. Isso é esperado e correto.\n\n"

    "Sua única tarefa é encontrar DADOS CONCRETOS que o post apresenta como fato e que "
    "não existem na fonte. Aplique este teste a cada frase, nesta ordem:\n"
    "1. A frase contém um dado concreto — número, porcentagem, data, versão de software, "
    "sistema operacional, modelo de dispositivo, navegador, nome de região, empresa, "
    "produto, incidente, caso ou benchmark? Se NÃO contém, pule a frase, não sinalize.\n"
    "2. Se contém, procure esse dado na fonte. Se estiver lá, no mesmo contexto, "
    "não sinalize.\n"
    "3. Sinalize apenas se o dado não estiver na fonte, ou se dois dados que existem "
    "separadamente na fonte forem combinados numa afirmação que ela não faz.\n\n"

    "Exemplo de conflação a sinalizar: a fonte diz que 14% dos usuários abandonam o "
    "pagamento e, em outro ponto, que há churn numa região; o post afirmar que 14% "
    "abandonam naquela região combina dois dados que a fonte não correlaciona.\n"
    "Justaposição também conta: dois fatos que a fonte apenas lista lado a lado, como "
    "sintomas distintos, não podem virar um só no post — nem como causa e efeito, nem "
    "como o mesmo fenômeno. Proximidade no texto da fonte não é ligação afirmada por "
    "ela. Verifique se a fonte diz que um se refere ao outro; se não disser, sinalize.\n\n"

    "NUNCA sinalize, mesmo que não esteja na fonte:\n"
    "- opinião, juízo de valor, crítica, discordância ou elogio;\n"
    "- projeção de risco e ressalva ('pode gerar', 'exige cuidado', 'sem isso, vira');\n"
    "- inferência e raciocínio causal do autor sobre o que a fonte descreve;\n"
    "- implicação prática, recomendação ou conclusão do autor;\n"
    "- a quem o assunto interessa ('equipes de SRE', 'times de segurança') — "
    "isso é enquadramento para o leitor, não afirmação sobre a fonte;\n"
    "- afirmação sobre o que a fonte deixa de detalhar, quando for verdade;\n"
    "- reformulação fiel do conteúdo da fonte em outras palavras;\n"
    "- conhecimento técnico geral e incontroverso da área;\n"
    "- a URL no final do post.\n\n"

    "Ausência na fonte só é problema para DADO CONCRETO. Para todo o resto, a ausência "
    "é normal: é o autor pensando, não relatando. Na dúvida, NÃO sinalize. "
    "Sinalize apenas o que um leitor que abrisse a fonte apontaria como falso — "
    "nunca o que ele apontaria apenas como não mencionado.\n\n"

    "SAÍDA: se nada for sinalizado, responda exatamente OK e nada mais. Caso contrário, "
    "liste uma afirmação por linha, cada linha começando com '- ', citando o dado "
    "problemático e dizendo em poucas palavras por que. Sem preâmbulo, sem conclusão."
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
