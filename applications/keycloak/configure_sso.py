"""Reconcile central SSO metadata using an authenticated kc callable.

Does not change credentials, users, Vault auth methods or service-account grants.
Deploy the redirect-based Web before disabling the old iframe exception.
"""


def configure(kc):
    realm = kc("GET", "finops")
    headers = dict(realm["browserSecurityHeaders"])
    directives = [d.strip() for d in headers["contentSecurityPolicy"].split(";") if d.strip()]
    directives = [d for d in directives if d.split()[0] != "frame-ancestors"]
    directives.append("frame-ancestors 'self'")
    headers["contentSecurityPolicy"] = "; ".join(directives) + ";"
    headers["xFrameOptions"] = "SAMEORIGIN"
    kc("PUT", "finops", {"browserSecurityHeaders": headers})
    for name, origin, callback in [
        ("finops-web", "https://app.sniper541.com", "/"),
        ("kafka-ui", "https://kafka.sniper541.com", "/login/oauth2/code/keycloak"),
        ("vault", "https://vault.sniper541.com", "/ui/vault/auth/oidc/oidc/callback"),
    ]:
        clients = kc("GET", "finops/clients?clientId=" + name)
        if len(clients) != 1:
            raise RuntimeError("Expected exactly one client: " + name)
        client = clients[0]
        attributes = dict(client.get("attributes", {}))
        attributes["post.logout.redirect.uris"] = origin + "/"
        if name == "finops-web":
            attributes["pkce.code.challenge.method"] = "S256"
        kc("PUT", "finops/clients/" + client["id"], {
            "rootUrl": origin, "baseUrl": origin + "/",
            "redirectUris": [origin + callback],
            "webOrigins": [origin] if name == "finops-web" else [],
            "publicClient": name == "finops-web", "standardFlowEnabled": True,
            "implicitFlowEnabled": False, "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": False, "attributes": attributes,
        })
    assert kc("GET", "finops")["browserSecurityHeaders"] == headers
    print("Central SSO client boundaries and anti-framing policy verified")
