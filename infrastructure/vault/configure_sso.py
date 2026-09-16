"""Coordinated canonical issuer cutover; call with authenticated kc and v APIs.

Deploy compatible Web first, then apply API/bot issuer configuration alongside
this operation. Existing old-issuer access tokens require reauthentication.
No password grant or client-secret rotation is enabled here.
"""
ISSUER = "https://auth.sniper541.com/realms/finops"
CALLBACK = "https://vault.sniper541.com/ui/vault/auth/oidc/oidc/callback"


def configure(kc, v):
    client = kc("GET", "finops/clients?clientId=vault")[0]
    client.update(publicClient=False, standardFlowEnabled=True,
                  directAccessGrantsEnabled=False, serviceAccountsEnabled=False,
                  redirectUris=[CALLBACK], webOrigins=["https://vault.sniper541.com"])
    base = "finops/clients/" + client["id"]
    kc("PUT", base, client)
    secret = kc("GET", base + "/client-secret")["value"]
    realm = kc("GET", "finops")
    realm.setdefault("attributes", {}).pop("frontendUrl", None)
    kc("PUT", "finops", realm)
    v("POST", "auth/oidc/config", {
        "oidc_discovery_url": ISSUER, "bound_issuer": ISSUER,
        "oidc_client_id": "vault", "oidc_client_secret": secret,
        "default_role": "vault-admin",
    })
    del secret
    v("POST", "sys/auth/oidc/tune", {"listing_visibility": "unauth"})
    print("Canonical Keycloak issuer and Vault discovery configured; client secret retained")
