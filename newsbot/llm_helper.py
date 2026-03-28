import os
import sys
import time

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


GROQ_MODEL   = os.getenv("GROQ_MODEL")   or "llama-3.3-70b-versatile"
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

_RETRY_DELAYS = [5, 15]


def _groq_call(groq, messages, temperature, max_tokens):
    for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
        if delay:
            time.sleep(delay)
        try:
            resp = groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip() or None
        except Exception as e:
            print(f"[llm] Groq tentativa {attempt} falhou ({e.__class__.__name__}): {e}", file=sys.stderr)
    return None


def chat(messages: list, temperature: float = 0.7, max_tokens: int = 700) -> str | None:
    groq = _groq()
    if groq:
        result = _groq_call(groq, messages, temperature, max_tokens)
        if result:
            return result
        print("[llm] Groq esgotou tentativas — tentando OpenAI...", file=sys.stderr)

    openai = _openai()
    if openai:
        try:
            resp = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip() or None
        except Exception as e:
            print(f"[llm] OpenAI falhou: {e}", file=sys.stderr)

    print("[llm] Nenhum provedor disponivel.", file=sys.stderr)
    return None
