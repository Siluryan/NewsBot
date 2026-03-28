#!/usr/bin/env python3
import threading
import webbrowser
import requests
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

CLIENT_ID     = os.environ.get("LINKEDIN_CLIENT_ID") or input("LINKEDIN_CLIENT_ID: ").strip()
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET") or input("LINKEDIN_CLIENT_SECRET: ").strip()
SCOPE    = "openid profile w_member_social"
REDIRECT = "http://localhost:8765/callback"
AUTH     = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN    = "https://www.linkedin.com/oauth/v2/accessToken"

code_holder = {"code": None}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code_holder["code"] = (qs.get("code") or [""])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK. Volte ao terminal.")

    def log_message(self, format, *args):
        pass


def serve():
    HTTPServer(("127.0.0.1", 8765), H).serve_forever()


def main():
    threading.Thread(target=serve, daemon=True).start()
    url = (
        f"{AUTH}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT, safe='')}"
        f"&scope={urllib.parse.quote(SCOPE, safe=' ')}&state=xyz123"
    )
    print("Abrindo:", url)
    webbrowser.open(url)
    print("Aguarde a autorizacao e o redirecionamento...")
    while not code_holder["code"]:
        pass
    code = code_holder["code"]
    r = requests.post(TOKEN, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }, timeout=30)
    r.raise_for_status()
    tok = r.json()["access_token"]

    person_id = None
    try:
        me = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {tok}"},
            timeout=10,
        ).json()
        person_id = me.get("sub") or me.get("id")
    except Exception:
        pass

    if not person_id:
        print("Nao foi possivel obter o ID automaticamente.")
        print("Acesse: https://www.linkedin.com/in/SEU_USUARIO/")
        print("Clique com botao direito, Ver codigo-fonte, busque por 'entityUrn' ou 'memberId'")
        person_id = input("Cole aqui apenas o ID numerico/alfanumerico: ").strip()

    person_urn = f"urn:li:person:{person_id}"
    print("\n=============================")
    print("ACCESS_TOKEN:", tok)
    print("LINKEDIN_MEMBER_URN:", person_urn)
    print("=============================")
    print("Copie os valores acima e adicione nos segredos do GitHub Actions.")


if __name__ == "__main__":
    main()
