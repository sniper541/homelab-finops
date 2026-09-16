"""Reconcile dedicated Vault authorization using authenticated API callables.

Operator supplies kc(method, relative_realm_path, body) and
v(method, relative_vault_v1_path, body). Never persists credentials.
Run before changing discovery/issuer; it preserves the current working issuer.
"""


def configure(kc, v, admin_username="mikhail"):
    clients = kc("GET", "finops/clients?clientId=vault")
    if len(clients) != 1:
        raise RuntimeError("Expected exactly one Vault client")
    client = clients[0]
    base = "finops/clients/" + client["id"]
    users = kc("GET", "finops/users?username=" + admin_username + "&exact=true")
    if len(users) != 1 or not users[0].get("enabled"):
        raise RuntimeError("Expected one enabled designated Vault administrator")
    roles = kc("GET", base + "/roles")
    if not any(role["name"] == "vault-admin" for role in roles):
        kc("POST", base + "/roles", {
            "name": "vault-admin", "description": "Explicit access to Vault administration"
        })
    role = kc("GET", base + "/roles/vault-admin")
    mapping = "finops/users/" + users[0]["id"] + "/role-mappings/clients/" + client["id"]
    if not any(r["id"] == role["id"] for r in kc("GET", mapping)):
        kc("POST", mapping, [role])
    mapper = {
        "name": "vault-authorization", "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-client-role-mapper",
        "consentRequired": False,
        "config": {
            "usermodel.clientRoleMapping.clientId": "vault",
            "claim.name": "vault_roles", "jsonType.label": "String",
            "multivalued": "true", "id.token.claim": "true",
            "access.token.claim": "false", "userinfo.token.claim": "true",
        },
    }
    existing = [m for m in kc("GET", base + "/protocol-mappers/models")
                if m["name"] == mapper["name"]]
    if existing:
        mapper["id"] = existing[0]["id"]
        kc("PUT", base + "/protocol-mappers/models/" + mapper["id"], mapper)
    else:
        kc("POST", base + "/protocol-mappers/models", mapper)
    current = v("GET", "auth/oidc/role/vault-admin")["data"]
    current.update({
        "role_type": "oidc", "user_claim": "sub",
        "bound_audiences": ["vault"],
        "bound_claims_type": "string",
        "bound_claims": {"vault_roles": ["vault-admin"]},
        "allowed_redirect_uris": [
            "https://vault.sniper541.com/ui/vault/auth/oidc/oidc/callback"
        ],
        "oidc_scopes": ["openid", "profile", "email"],
        "token_policies": ["vault-admin"],
        "token_ttl": 3600, "token_max_ttl": 14400,
        "verbose_oidc_logging": False,
    })
    v("POST", "auth/oidc/role/vault-admin", current)
    actual = v("GET", "auth/oidc/role/vault-admin")["data"]
    if actual["bound_claims"] != {"vault_roles": ["vault-admin"]}:
        raise RuntimeError("Vault authorization verification failed")
    print("Vault OIDC restricted to explicit vault/vault-admin role; verified")
