"""Idempotent non-secret realm policy; invoke with an authenticated Admin REST client.

Credentials belong to the operator's session, never this module. Origin migration
is explicit and must follow the reverse-proxy smoke test and route deployment.
"""
PUBLIC_ORIGIN = "https://app.sniper541.com"
FRONTEND_URL = PUBLIC_ORIGIN + "/auth"


def configure(kc, *, switch_origin=False):
    def client(client_id, fields):
        found = kc("GET", "finops/clients?clientId=" + client_id)
        if not found:
            kc("POST", "finops/clients", {"clientId":client_id,"enabled":True,"protocol":"openid-connect",**fields})
            found = kc("GET", "finops/clients?clientId=" + client_id)
        current=found[0]
        current.update(fields)
        kc("PUT", "finops/clients/"+current["id"],current)
        return current

    api=client("finops-api",{"bearerOnly":True,"standardFlowEnabled":False,"directAccessGrantsEnabled":False,
                            "serviceAccountsEnabled":False,"publicClient":False})
    scopes=kc("GET","finops/client-scopes")
    scope=next((s for s in scopes if s['name']=='finops-api-access'),None)
    if scope is None:
        kc("POST","finops/client-scopes",{"name":"finops-api-access","protocol":"openid-connect",
            "attributes":{"include.in.token.scope":"true","display.on.consent.screen":"false"}})
        scope=next(s for s in kc("GET","finops/client-scopes") if s['name']=='finops-api-access')
    mapper={"name":"finops-api-audience","protocol":"openid-connect","protocolMapper":"oidc-audience-mapper",
            "config":{"included.client.audience":"finops-api","access.token.claim":"true","id.token.claim":"false","introspection.token.claim":"true"}}
    mapper_path=f"finops/client-scopes/{scope['id']}/protocol-mappers/models"
    existing=next((m for m in kc("GET",mapper_path) if m['name']==mapper['name']),None)
    if existing:
        kc("PUT",mapper_path+'/'+existing['id'],{**mapper,'id':existing['id']})
    else:
        kc("POST",mapper_path,mapper)
    web=kc("GET","finops/clients?clientId=finops-web")[0]
    web.update(publicClient=True,standardFlowEnabled=True,directAccessGrantsEnabled=False,serviceAccountsEnabled=False,
               redirectUris=[PUBLIC_ORIGIN+'/'],webOrigins=[PUBLIC_ORIGIN])
    web.setdefault('attributes',{}).update({'pkce.code.challenge.method':'S256','post.logout.redirect.uris':PUBLIC_ORIGIN+'/'})
    kc("PUT",'finops/clients/'+web['id'],web)
    kc("PUT",f"finops/clients/{web['id']}/default-client-scopes/{scope['id']}")
    bot=client("finops-bot",{"publicClient":False,"bearerOnly":False,"clientAuthenticatorType":"client-secret",
        "serviceAccountsEnabled":True,"standardFlowEnabled":False,"directAccessGrantsEnabled":False,
        "fullScopeAllowed":False,"defaultClientScopes":["basic","roles","service_account"]})
    kc("PUT",f"finops/clients/{bot['id']}/default-client-scopes/{scope['id']}")
    role_path=f"finops/clients/{api['id']}/roles"
    if not any(r['name']=='telegram-bot' for r in kc("GET",role_path)):
        kc("POST",role_path,{'name':'telegram-bot','description':'Trusted Telegram polling service only'})
    role=kc("GET",role_path+'/telegram-bot')
    user=kc("GET",f"finops/clients/{bot['id']}/service-account-user")
    kc("POST",f"finops/users/{user['id']}/role-mappings/clients/{api['id']}",[role])
    kc("POST",f"finops/clients/{bot['id']}/scope-mappings/clients/{api['id']}",[role])
    realm=kc("GET","finops")
    realm.update(bruteForceProtected=True,permanentLockout=False,failureFactor=5,waitIncrementSeconds=60,maxFailureWaitSeconds=900)
    if switch_origin:
        realm.setdefault('attributes',{})['frontendUrl']=FRONTEND_URL
    kc("PUT","finops",realm)
    print('Configured API audience, PKCE enforcement, bot service role and brute-force protection; origin changed:',switch_origin)
    return bot['id']
