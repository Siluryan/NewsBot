#!/usr/bin/env python3
import os
import sys
import time
import urllib.parse
import requests


def get_token_via_playwright(
    client_id: str,
    client_secret: str,
    scope: str,
    email: str,
    password: str,
) -> str:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    redirect_uri = "http://localhost:8765/callback"
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
        f"&scope={urllib.parse.quote(scope, safe=' ')}"
        f"&state=autorenew"
    )

    code = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def handle_request(request):
            nonlocal code
            url = request.url
            if "localhost:8765/callback" in url and "code=" in url:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                code = (qs.get("code") or [""])[0]

        page.on("request", handle_request)

        print("Navegando para URL de autorizacao...")
        try:
            page.goto(auth_url, timeout=15000)
        except Exception:
            pass

        try:
            page.wait_for_selector('input[name="session_key"]', timeout=10000)
            page.fill('input[name="session_key"]', email)
            page.fill('input[name="session_password"]', password)
            page.click('button[type="submit"]')
            print("Login submetido.")
        except PWTimeout:
            print("Campo de login nao encontrado — possivelmente ja autenticado.")

        try:
            page.wait_for_selector(
                'button:has-text("Allow"), button:has-text("Autorizar"), '
                'button[data-litms-control-urn*="allow"], '
                'button[action-type="ALLOW"]',
                timeout=10000,
            )
            page.click(
                'button:has-text("Allow"), button:has-text("Autorizar"), '
                'button[data-litms-control-urn*="allow"], '
                'button[action-type="ALLOW"]'
            )
            print("App autorizado.")
        except PWTimeout:
            print("Botao de autorizacao nao encontrado — pode ja estar autorizado.")

        for _ in range(30):
            if code:
                break
            time.sleep(0.5)

        browser.close()

    if not code:
        print("Nao foi possivel capturar o code OAuth.", file=sys.stderr)
        print("Verifique se ha 2FA ou CAPTCHA ativo na conta.", file=sys.stderr)
        sys.exit(1)

    print("Code capturado com sucesso.")

    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token", "")
    if not token:
        print(f"Resposta inesperada: {resp.text}", file=sys.stderr)
        sys.exit(1)

    return token


def update_github_secret(repo: str, secret_name: str, secret_value: str, pat: str):
    from nacl import encoding, public
    import base64

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
    pub_key = public.PublicKey(key_data["key"].encode(), encoding.Base64Encoder)
    encrypted = base64.b64encode(public.SealedBox(pub_key).encrypt(secret_value.encode())).decode()

    r2 = requests.put(
        f"{base}/actions/secrets/{secret_name}",
        headers=headers,
        json={"encrypted_value": encrypted, "key_id": key_id},
        timeout=15,
    )
    if r2.status_code in (201, 204):
        print(f"Secret '{secret_name}' atualizado no GitHub.")
    else:
        print(f"Falha ao atualizar secret: {r2.status_code} {r2.text}", file=sys.stderr)
        sys.exit(1)


def main():
    email         = os.environ["LINKEDIN_EMAIL"]
    password      = os.environ["LINKEDIN_PASSWORD"]
    client_id     = os.environ["LINKEDIN_CLIENT_ID"]
    client_secret = os.environ["LINKEDIN_CLIENT_SECRET"]
    scope         = os.environ.get("LINKEDIN_SCOPE", "openid profile w_member_social")
    pat           = os.environ.get("GITHUB_PAT", "")
    repo          = os.environ.get("GITHUB_REPOSITORY", "")

    token = get_token_via_playwright(client_id, client_secret, scope, email, password)
    print(f"\nACCESS_TOKEN: {token}\n")

    gha_output = os.environ.get("GITHUB_OUTPUT", "")
    if gha_output:
        with open(gha_output, "a") as f:
            f.write(f"access_token={token}\n")

    if pat and repo:
        update_github_secret(repo, "LINKEDIN_ACCESS_TOKEN", token, pat)
    else:
        print("GITHUB_PAT ou GITHUB_REPOSITORY nao definidos — secret nao atualizado automaticamente.")
        print("Copie o ACCESS_TOKEN acima e atualize manualmente.")


if __name__ == "__main__":
    main()
