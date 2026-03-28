#!/usr/bin/env python3
import os
import sys
import requests
from datetime import datetime, timezone

LINKEDIN_API = "https://api.linkedin.com/v2"


def check_token(token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": "202401",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/introspectToken",
        data={
            "token": token,
            "client_id": os.environ.get("LINKEDIN_CLIENT_ID", ""),
            "client_secret": os.environ.get("LINKEDIN_CLIENT_SECRET", ""),
        },
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json()
    r2 = requests.get(f"{LINKEDIN_API}/me", headers=headers, timeout=15)
    if r2.status_code in (200, 403):
        return {"active": True, "expires_at": None}
    return {"active": False}


def main():
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    if not token:
        print("LINKEDIN_ACCESS_TOKEN nao definido.", file=sys.stderr)
        sys.exit(1)

    info = check_token(token)
    active = info.get("active", True)

    if not active:
        print("Token INVALIDO ou EXPIRADO.", file=sys.stderr)
        print("Rode python3 scripts/get_linkedin_token.py localmente para gerar um novo token", file=sys.stderr)
        print("e atualize o secret LINKEDIN_ACCESS_TOKEN no GitHub.", file=sys.stderr)
        sys.exit(1)

    expires_at = info.get("expires_at")
    if expires_at:
        now = datetime.now(timezone.utc).timestamp()
        days_left = int((expires_at - now) / 86400)
        print(f"Token valido. Expira em ~{days_left} dias.")
        if days_left < 14:
            print(f"Token expira em {days_left} dias. Renove em breve.", file=sys.stderr)
            gha_output = os.environ.get("GITHUB_OUTPUT", "")
            if gha_output:
                with open(gha_output, "a") as f:
                    f.write(f"token_expiring_soon=true\n")
                    f.write(f"days_left={days_left}\n")
    else:
        print("Token valido (sem info de expiracao).")


if __name__ == "__main__":
    main()
