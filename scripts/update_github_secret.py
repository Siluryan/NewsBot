#!/usr/bin/env python3
import os
import sys
import base64
import requests
from nacl import encoding, public


def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    public_key = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder)
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode())
    return base64.b64encode(encrypted).decode()


def update_secret(repo: str, secret_name: str, secret_value: str, pat: str):
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    base = f"https://api.github.com/repos/{repo}"

    r = requests.get(f"{base}/actions/secrets/public-key", headers=headers, timeout=15)
    r.raise_for_status()
    key_data = r.json()
    key_id = key_data["key_id"]
    public_key_b64 = key_data["key"]

    encrypted = encrypt_secret(public_key_b64, secret_value)

    payload = {"encrypted_value": encrypted, "key_id": key_id}
    r2 = requests.put(
        f"{base}/actions/secrets/{secret_name}",
        headers=headers,
        json=payload,
        timeout=15,
    )
    if r2.status_code in (201, 204):
        print(f"Secret '{secret_name}' atualizado no repositorio '{repo}'.")
    else:
        print(f"Falha ao atualizar secret: {r2.status_code} {r2.text}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/update_github_secret.py SECRET_NAME valor", file=sys.stderr)
        sys.exit(1)

    secret_name = sys.argv[1]
    secret_value = sys.argv[2]
    pat = os.environ.get("GITHUB_PAT", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if not pat:
        print("GITHUB_PAT nao definido.", file=sys.stderr)
        sys.exit(1)
    if not repo:
        print("GITHUB_REPOSITORY nao definido (ex.: usuario/repo).", file=sys.stderr)
        sys.exit(1)

    update_secret(repo, secret_name, secret_value, pat)


if __name__ == "__main__":
    main()
