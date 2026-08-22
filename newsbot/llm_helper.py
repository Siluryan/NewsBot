import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from groq import Groq

_groq_client = None
_openai_client = None


def _groq():
    global _groq_client
    if _groq_client is None and os.getenv("GROQ_API_KEY"):
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client


def _openai():
    global _openai_client
    if _openai_client is None and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except ImportError:
            print(
                "[llm] OPENAI_API_KEY definido mas pacote `openai` nao instalado — "
                "fallback indisponivel.",
                file=sys.stderr,
            )
    return _openai_client


GROQ_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT") or "low"

GROQ_MODEL          = os.getenv("GROQ_MODEL")          or "openai/gpt-oss-120b"
GROQ_MODEL_FALLBACK = os.getenv("GROQ_MODEL_FALLBACK") or "openai/gpt-oss-20b"
OPENAI_MODELS       = [
    os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
    "gpt-4o",
    "gpt-3.5-turbo",
    "gpt-4-turbo",
]


def _groq_call(groq, model, messages, temperature, max_tokens):
    try:
        print(f"[llm] Usando Groq ({model})...", file=sys.stderr)
        extra = {}
        if "gpt-oss" in model:
            # Modelos de raciocinio gastam tokens pensando antes de escrever, e esses
            # tokens saem do mesmo orcamento de max_tokens. Com o default (medium) o
            # raciocinio consome a cota e sobra conteudo truncado ou vazio.
            extra["reasoning_effort"] = GROQ_REASONING_EFFORT
        resp = groq.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra,
        )
        choice = resp.choices[0]
        if choice.finish_reason == "length":
            print(
                f"[llm] Groq ({model}) estourou max_tokens={max_tokens} "
                f"(finish_reason=length) — descartando saida truncada.",
                file=sys.stderr,
            )
            return None
        result = (choice.message.content or "").strip() or None
        if not result:
            print(f"[llm] Groq ({model}) devolveu conteudo vazio.", file=sys.stderr)
            return None
        print(f"[llm] Groq ({model}) OK.", file=sys.stderr)
        return result
    except Exception as e:
        print(f"[llm] Groq ({model}) falhou ({e.__class__.__name__}): {e}", file=sys.stderr)
        return None


def chat(messages: list, temperature: float = 0.7, max_tokens: int = 700) -> str | None:
    groq = _groq()
    if groq:
        result = _groq_call(groq, GROQ_MODEL, messages, temperature, max_tokens)
        if result:
            return result
        result = _groq_call(groq, GROQ_MODEL_FALLBACK, messages, temperature, max_tokens)
        if result:
            return result
        print("[llm] Groq esgotou — tentando OpenAI...", file=sys.stderr)

    openai = _openai()
    if openai:
        for model in OPENAI_MODELS:
            try:
                print(f"[llm] Usando OpenAI ({model})...", file=sys.stderr)
                resp = openai.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                choice = resp.choices[0]
                if choice.finish_reason == "length":
                    print(
                        f"[llm] OpenAI ({model}) estourou max_tokens={max_tokens} "
                        f"(finish_reason=length) — descartando saida truncada.",
                        file=sys.stderr,
                    )
                    continue
                result = (choice.message.content or "").strip() or None
                if not result:
                    print(f"[llm] OpenAI ({model}) devolveu conteudo vazio.", file=sys.stderr)
                    continue
                print(f"[llm] OpenAI ({model}) OK.", file=sys.stderr)
                return result
            except Exception as e:
                print(f"[llm] OpenAI ({model}) falhou: {e}", file=sys.stderr)

    print("[llm] Nenhum provedor disponivel.", file=sys.stderr)
    return None
