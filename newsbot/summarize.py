import os
from typing import Optional
from .llm_helper import chat

_DEFAULT_PROMPT = (
    "Você é um editor técnico que escreve resumos curtos (1–2 frases corridas, sem bullets) "
    "sobre DevOps, SRE e Cloud, com foco em segurança, arquitetura e boas práticas. "
    "Se o artigo mencionar Inteligência Artificial, Machine Learning ou LLMs, ignore esses aspectos "
    "e foque exclusivamente nas implicações de infraestrutura, segurança ou confiabilidade. "
    "Produza texto natural, com tom humano/profissional, destacando o porquê importa e para quem. "
    "Responda em português brasileiro e evite jargões excessivos. "
    "Escreva no máximo 400 caracteres. Duas frases curtas, não uma longa: "
    "não emende ideias com ponto e vírgula para alongar o texto."
)

SYSTEM_PROMPT = os.getenv("SUMMARIZE_PROMPT") or _DEFAULT_PROMPT


def summarize_text(title: str, url: str, text: Optional[str], max_tokens: int = 1000) -> Optional[str]:
    return chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Título: {title}\n"
                f"URL: {url}\n\n"
                f"Conteúdo (pode estar truncado):\n{(text or '')[:4000]}"
            )},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )
