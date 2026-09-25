"""
Driver de agente para subir, autenticar e dirigir o SAGA (backend + frontend).

Responsabilidades:
- up/down/status: sobe e derruba uvicorn (:8000) e Vite (:5173) em background,
  guardando PIDs e logs em <tmp>/saga-run/.
- token: emite um ID token Firebase para uma conta existente SEM senha
  (Admin SDK custom token -> REST signInWithCustomToken). Não altera a conta.
- api: chama a API com esse token (curl autenticado).
- shot: abre o frontend no Chromium headless (Playwright), loga a conta via
  custom token, clica em textos (sidebar/abas) e tira screenshot.

Uso (a partir da raiz do repo):
    uv run --with playwright python .claude/skills/run-saga/driver.py <comando> ...
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUN_DIR = Path(tempfile.gettempdir()) / "saga-run"
PIDS = RUN_DIR / "pids.json"
API = "http://localhost:8000"
WEB = "http://localhost:5173"

# Login dentro da página: reusa a MESMA instância de firebase/auth do app
# (URL pré-empacotada pelo Vite, com o ?v=hash), senão o app não vê o login.
BROWSER_LOGIN_JS = """
async (token) => {
  const src = await (await fetch('/src/lib/firebase.ts')).text();
  const m = src.match(/from\\s+["'](\\/node_modules\\/\\.vite\\/deps\\/firebase_auth\\.js[^"']*)["']/);
  if (!m) throw new Error('firebase_auth dep URL not found in /src/lib/firebase.ts');
  const fa = await import(m[1]);
  const { auth } = await import('/src/lib/firebase.ts');
  await fa.signInWithCustomToken(auth, token);
  return auth.currentUser && auth.currentUser.email;
}
"""


LOADING_TEXT = re.compile(r"^\s*(Carregando|Consultando)")


def read_env() -> dict[str, str]:
    """Lê o .env da raiz (só chave=valor simples; aspas removidas)."""
    env: dict[str, str] = {}
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def http(method: str, url: str, body: dict | None = None, token: str | None = None) -> tuple[int, str]:
    """Faz uma requisição HTTP e devolve (status, corpo)."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


def is_up(url: str) -> bool:
    """True se a URL responde (qualquer status HTTP)."""
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def spawn(name: str, cmd: list[str]) -> int:
    """Sobe um processo destacado, logando em RUN_DIR/<name>.log."""
    log = open(RUN_DIR / f"{name}.log", "w", encoding="utf-8")
    kwargs: dict = {"cwd": REPO, "stdout": log, "stderr": subprocess.STDOUT, "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs).pid


def cmd_up(_: argparse.Namespace) -> None:
    RUN_DIR.mkdir(exist_ok=True)
    pids: dict[str, int] = {}
    if is_up(f"{API}/api/v1/health"):
        print("backend já está no ar em :8000 (não foi iniciado por mim)")
    else:
        uv = shutil.which("uv") or "uv"
        pids["backend"] = spawn("backend", [uv, "run", "uvicorn", "backend.app.main:app", "--port", "8000"])
    if is_up(WEB):
        print("frontend já está no ar em :5173 (não foi iniciado por mim)")
    else:
        pnpm = shutil.which("pnpm") or "pnpm"
        pids["frontend"] = spawn("frontend", [pnpm, "dev", "--port", "5173", "--strictPort"])
    PIDS.write_text(json.dumps(pids))
    deadline = time.time() + 90
    while time.time() < deadline and not (is_up(f"{API}/api/v1/health") and is_up(WEB)):
        time.sleep(1)
    cmd_status(_)


def kill_tree(pid: int) -> None:
    """Mata o processo e seus filhos (uv->python, pnpm->node)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
    else:
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def cmd_down(_: argparse.Namespace) -> None:
    pids = json.loads(PIDS.read_text()) if PIDS.exists() else {}
    for name, pid in pids.items():
        kill_tree(pid)
        print(f"parado: {name} (pid {pid})")
    PIDS.unlink(missing_ok=True)
    if not pids:
        print("nada iniciado por este driver")


def cmd_status(_: argparse.Namespace) -> None:
    status, body = http("GET", f"{API}/api/v1/health") if is_up(f"{API}/api/v1/health") else (0, "down")
    print(f"backend  {API}  {status} {body}")
    print(f"frontend {WEB}  {'up' if is_up(WEB) else 'down'}")
    print(f"logs     {RUN_DIR}")


def custom_token(email: str) -> str:
    """Cria um custom token Admin SDK para a conta com esse e-mail."""
    sys.path.insert(0, str(REPO))
    os.chdir(REPO)
    from firebase_admin import auth

    from backend.app.core.firebase import init_firebase

    init_firebase()
    uid = auth.get_user_by_email(email).uid
    return auth.create_custom_token(uid).decode()


def id_token(email: str) -> str:
    """Troca o custom token por um ID token (com as custom claims da conta)."""
    key = read_env()["VITE_FIREBASE_API_KEY"]
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={key}"
    status, body = http("POST", url, {"token": custom_token(email), "returnSecureToken": True})
    if status != 200:
        sys.exit(f"signInWithCustomToken falhou ({status}): {body}")
    return json.loads(body)["idToken"]


def cmd_token(args: argparse.Namespace) -> None:
    print(id_token(args.as_email))


def cmd_api(args: argparse.Namespace) -> None:
    token = id_token(args.as_email) if args.as_email else None
    path = args.path if args.path.startswith("/api") else f"/api/v1/{args.path.lstrip('/')}"
    body = json.loads(args.data) if args.data else None
    status, text = http(args.method.upper(), f"{API}{path}", body, token)
    print(status)
    try:
        print(json.dumps(json.loads(text), indent=2, ensure_ascii=False)[: args.max])
    except ValueError:
        print(text[: args.max])


def track_api(page: object) -> set:
    """Mantém o conjunto de requisições /api/ em andamento na página."""
    pending: set = set()
    page.on("request", lambda r: "/api/" in r.url and pending.add(r))
    page.on("requestfinished", lambda r: pending.discard(r))
    page.on("requestfailed", lambda r: pending.discard(r))
    return pending


def settle(page: object, pending: set, quiet_ms: int = 800, timeout_s: int = 30) -> None:
    """Espera a API ficar quieta por `quiet_ms` e os placeholders "Carregando…"/"Consultando…" sumirem.

    Em SPA, wait_for_load_state("networkidle") após um clique é no-op (não há navegação),
    por isso as requisições /api/ são contadas à mão.
    """
    deadline = time.time() + timeout_s
    quiet_since = time.time()
    while time.time() < deadline:
        page.wait_for_timeout(100)
        if pending:
            quiet_since = time.time()
        elif (time.time() - quiet_since) * 1000 >= quiet_ms and page.get_by_text(LOADING_TEXT).count() == 0:
            return
    print(f"[aviso] tela não assentou em {timeout_s}s (API pendente ou placeholder visível)")


def cmd_shot(args: argparse.Namespace) -> None:
    from playwright.sync_api import sync_playwright

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    token = custom_token(args.as_email) if args.as_email else None
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: m.type == "error" and print(f"[console.error] {m.text}"))
        pending = track_api(page)
        page.goto(WEB, wait_until="networkidle")
        if token:
            print("logado como:", page.evaluate(BROWSER_LOGIN_JS, token))
            # O app troca para o dashboard quando o perfil (/auth/me) carrega.
            page.get_by_text("Entrar no Sistema").wait_for(state="detached", timeout=30000)
            settle(page, pending)
        for text in args.click:
            page.get_by_text(text, exact=True).first.click()
            settle(page, pending)
        if args.wait:
            page.get_by_text(args.wait).first.wait_for(timeout=30000)
        page.screenshot(path=str(out), full_page=args.full)
        if args.text:
            print(page.inner_text("main") if page.locator("main").count() else page.inner_text("body"))
        browser.close()
    print(f"screenshot: {out}")


def main() -> None:
    # Console do Windows é cp1252: sem isto, acentos da API/UI quebram o print.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("up").set_defaults(func=cmd_up)
    sub.add_parser("down").set_defaults(func=cmd_down)
    sub.add_parser("status").set_defaults(func=cmd_status)

    token = sub.add_parser("token")
    token.add_argument("--as", dest="as_email", required=True)
    token.set_defaults(func=cmd_token)

    api = sub.add_parser("api")
    api.add_argument("method")
    api.add_argument("path", help="ex.: students  ou  /api/v1/students")
    api.add_argument("--as", dest="as_email")
    api.add_argument("--data", help="corpo JSON")
    api.add_argument("--max", type=int, default=4000, help="trunca a saída")
    api.set_defaults(func=cmd_api)

    shot = sub.add_parser("shot")
    shot.add_argument("out")
    shot.add_argument("--as", dest="as_email")
    shot.add_argument("--click", action="append", default=[], help="texto exato a clicar (repetível, em ordem)")
    shot.add_argument("--wait", help="texto que deve aparecer antes do screenshot")
    shot.add_argument("--full", action="store_true", help="página inteira")
    shot.add_argument("--text", action="store_true", help="imprime o texto visível ao final")
    shot.set_defaults(func=cmd_shot)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
