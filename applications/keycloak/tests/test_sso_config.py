"""Offline guard for client boundaries; run with python3 applications/keycloak/tests/test_sso_config.py."""
import copy
import runpy
from pathlib import Path

configure = runpy.run_path(str(Path(__file__).parents[1] / "configure_sso.py"))["configure"]
realm = {"browserSecurityHeaders": {"contentSecurityPolicy": "object-src 'none'; frame-ancestors https://app.sniper541.com;", "xFrameOptions": ""}}
clients = {name: {"id": name, "clientId": name, "secret": "unchanged-test-value", "attributes": {"preserve": "yes"}} for name in ["finops-web", "kafka-ui", "vault"]}


def kc(method, path, body=None):
    if path == "finops":
        if method == "PUT": realm.update(copy.deepcopy(body))
        return copy.deepcopy(realm)
    if "?clientId=" in path:
        return [copy.deepcopy(clients[path.split("=")[1]])]
    assert method == "PUT" and path.startswith("finops/clients/")
    assert "secret" not in body
    clients[path.rsplit("/", 1)[1]].update(copy.deepcopy(body))


configure(kc)
configure(kc)
for name, c in clients.items():
    assert c["secret"] == "unchanged-test-value"
    assert c["attributes"]["preserve"] == "yes"
    assert c["publicClient"] == (name == "finops-web")
    assert c["standardFlowEnabled"] and not c["directAccessGrantsEnabled"]
    assert len(c["redirectUris"]) == 1 and "*" not in c["redirectUris"][0]
assert clients["finops-web"]["attributes"]["pkce.code.challenge.method"] == "S256"
assert clients["kafka-ui"]["redirectUris"] == ["https://kafka.sniper541.com/login/oauth2/code/keycloak"]
assert clients["vault"]["redirectUris"] == ["https://vault.sniper541.com/ui/vault/auth/oidc/oidc/callback"]
assert "https://app" not in realm["browserSecurityHeaders"]["contentSecurityPolicy"]
print("SSO configuration checks passed")
