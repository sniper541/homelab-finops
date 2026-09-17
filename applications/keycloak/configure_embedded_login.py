"""Run configure(kc) in the operator's authenticated admin session; no credentials here.

Allow only the FinOps app to embed this realm's native identity forms.
Keep the canonical issuer, redirects, Vault client and password grants unchanged.
"""


def configure(kc):
    realm = kc("GET", "finops")
    headers = dict(realm["browserSecurityHeaders"])
    directives = [d.strip() for d in headers["contentSecurityPolicy"].split(";") if d.strip()]
    directives = [d for d in directives if d.split()[0] != "frame-ancestors"]
    directives.append("frame-ancestors 'self' https://app.sniper541.com")
    headers["contentSecurityPolicy"] = "; ".join(directives) + ";"
    # Modern CSP restricts every ancestor; SAMEORIGIN would contradict the allowed app.
    headers["xFrameOptions"] = ""
    kc("PUT", "finops", {"browserSecurityHeaders": headers})
    assert kc("GET", "finops")["browserSecurityHeaders"] == headers
    print("Native forms may be embedded only by self and https://app.sniper541.com.")
