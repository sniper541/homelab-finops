"""Reconcile reviewed Vault settings using short-lived operator credentials.

Run from the server checkout. Inputs are hidden, never written to disk or logs.
Obtain a Vault admin token through OIDC, not the initialization root token.
Keycloak operations additionally require a short-lived Admin REST access token.
"""
import argparse
import getpass
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

from configure_database import configure as database
from configure_oidc_access import configure as oidc_access
from configure_sso import configure as sso
from configure_workloads import configure as workloads


def client(base, header, token):
    def request(method, path, body=None):
        headers = {header: token, "Content-Type": "application/json"}
        payload = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(base + path, method=method, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                return json.loads(data) if data else None
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"Operator API {method} {path}: HTTP {error.code}") from None
    return request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for action in ("database", "workloads", "oidc-access", "sso", "audit"):
        parser.add_argument("--" + action, action="store_true")
    args = parser.parse_args()
    if not any(vars(args).values()):
        parser.error("Choose at least one explicit operation")
    v = client("https://vault.sniper541.com/v1/", "X-Vault-Token",
               getpass.getpass("Short-lived Vault OIDC administrator token: "))
    if args.oidc_access or args.sso:
        kc = client("https://auth.sniper541.com/admin/realms/", "Authorization",
                    "Bearer " + getpass.getpass("Short-lived Keycloak Admin REST token: "))
        if args.oidc_access:
            oidc_access(kc, v)
        if args.sso:
            sso(kc, v)
    if args.database:
        def sql_admin(sql):
            result = subprocess.run([
                "kubectl", "--kubeconfig=/home/sniper541/.kube/config", "-n", "finops",
                "exec", "-i", "postgres-0", "--", "sh", "-c",
                'psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
            ], input=sql, text=True, capture_output=True)
            if result.returncode:
                raise RuntimeError("SQL bootstrap failed; sensitive output suppressed")
        database(v, sql_admin)
    if args.workloads:
        workloads(v)
    if args.audit:
        if "file/" not in v("GET", "sys/audit")["data"]:
            v("PUT", "sys/audit/file", {"type": "file", "options": {
                "file_path": "/vault/audit/audit.json", "mode": "0600", "log_raw": "false",
            }})
        policy = (Path(__file__).parent / "policies" / "raft-backup.hcl").read_text()
        v("PUT", "sys/policies/acl/raft-backup", {"policy": policy})
        print("Persistent audit and backup policy reconciled")


if __name__ == "__main__":
    main()
