"""Inicializa SOMENTE um InfluxDB local vazio. Não sobrescreve backend/.env."""
import json
import secrets
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8086"


def request(path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"
    req = urllib.request.Request(URL + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def main():
    env_path = ROOT / "backend" / ".env"
    if env_path.exists():
        raise SystemExit("backend/.env já existe. Nenhuma alteração foi feita.")
    if not request("/api/v2/setup")["allowed"]:
        raise SystemExit("InfluxDB já configurado. Use sua conta e configure backend/.env manualmente.")
    password = secrets.token_urlsafe(24)
    setup = request("/api/v2/setup", {
        "username": "arcade-admin", "password": password, "org": "arcadeos",
        "bucket": "telemetry", "retentionPeriodSeconds": 30 * 86400,
    })
    token = request("/api/v2/authorizations", {
        "orgID": setup["org"]["id"], "description": "ArcadeOS local - somente bucket telemetry",
        "permissions": [{"action": action, "resource": {"type": "buckets", "id": setup["bucket"]["id"], "orgID": setup["org"]["id"]}} for action in ("read", "write")],
    }, setup["auth"]["token"])["token"]
    example = (ROOT / "backend" / ".env.example").read_text(encoding="utf-8")
    env_path.write_text(example.replace("substitua-pelo-token-do-influxdb", token), encoding="utf-8")
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    (runtime / "local-access.txt").write_text(
        f"ArcadeOS - acesso LOCAL, não publicar\nInfluxDB: {URL}\nUsuário: arcade-admin\nSenha: {password}\nOrganização: arcadeos\nBucket: telemetry\nToken do backend salvo somente em backend/.env.\n",
        encoding="utf-8",
    )
    print("InfluxDB local inicializado. Token restrito ao bucket salvo em backend/.env.")
    print("Acesso ao painel salvo em .runtime/local-access.txt (ignorado pelo Git).")


if __name__ == "__main__":
    main()
