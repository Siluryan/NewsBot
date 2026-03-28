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
            pass
    return _openai_client


GROQ_MODEL          = os.getenv("GROQ_MODEL")          or "llama-3.3-70b-versatile"
GROQ_MODEL_FALLBACK = os.getenv("GROQ_MODEL_FALLBACK") or "llama-3.1-8b-instant"
OPENAI_MODELS       = [
    os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
    "gpt-4o",
    "gpt-3.5-turbo",
    "gpt-4-turbo",
]


def _groq_call(groq, model, messages, temperature, max_tokens):
    try:
        print(f"[llm] Usando Groq ({model})...", file=sys.stderr)
        resp = groq.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        result = resp.choices[0].message.content.strip() or None
        if result:
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
                result = resp.choices[0].message.content.strip() or None
                if result:
                    print(f"[llm] OpenAI ({model}) OK.", file=sys.stderr)
                return result
            except Exception as e:
                print(f"[llm] OpenAI ({model}) falhou: {e}", file=sys.stderr)

    print("[llm] Nenhum provedor disponivel.", file=sys.stderr)
    return None
