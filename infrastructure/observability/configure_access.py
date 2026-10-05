"""Run configure(kc, v, sql_admin) with authenticated in-memory operator callables.

No credentials are written to Git, stdout, process arguments or Kubernetes Secrets.
Reruns preserve Grafana's encryption key and the PostgreSQL monitoring password.
"""
import secrets


def configure(kc, v, sql_admin):
    clients = kc('GET', 'finops/clients?clientId=grafana')
    if not clients:
        kc('POST', 'finops/clients', {'clientId': 'grafana', 'protocol': 'openid-connect', 'enabled': True})
        clients = kc('GET', 'finops/clients?clientId=grafana')
    assert len(clients) == 1
    base = 'finops/clients/' + clients[0]['id']
    attributes = dict(clients[0].get('attributes', {}))
    attributes.update({'pkce.code.challenge.method': 'S256', 'post.logout.redirect.uris': 'https://grafana.sniper541.com/login?disableAutoLogin=true', 'use.refresh.tokens': 'true'})
    kc('PUT', base, {
        'publicClient': False, 'standardFlowEnabled': True, 'directAccessGrantsEnabled': False,
        'implicitFlowEnabled': False, 'serviceAccountsEnabled': False,
        'rootUrl': 'https://grafana.sniper541.com', 'baseUrl': 'https://grafana.sniper541.com/',
        'redirectUris': ['https://grafana.sniper541.com/login/generic_oauth'],
        'webOrigins': [], 'attributes': attributes,
    })
    roles = kc('GET', 'finops/roles')
    if not any(r['name'] == 'grafana-admin' for r in roles):
        kc('POST', 'finops/roles', {'name': 'grafana-admin', 'description': 'Explicit Grafana server administration'})
    role = kc('GET', 'finops/roles/grafana-admin')
    users = kc('GET', 'finops/users?username=mikhail&exact=true')
    assert len(users) == 1 and users[0]['enabled'] and users[0].get('email'), 'Enabled mikhail with email required'
    mapping = 'finops/users/' + users[0]['id'] + '/role-mappings/realm'
    if not any(r['name'] == role['name'] for r in kc('GET', mapping)):
        kc('POST', mapping, [role])
    mapper = {'name': 'grafana-realm-roles', 'protocol': 'openid-connect',
              'protocolMapper': 'oidc-usermodel-realm-role-mapper', 'consentRequired': False,
              'config': {'claim.name': 'grafana_roles', 'jsonType.label': 'String', 'multivalued': 'true',
                         'id.token.claim': 'true', 'access.token.claim': 'true', 'userinfo.token.claim': 'true'}}
    existing = [m for m in kc('GET', base + '/protocol-mappers/models') if m['name'] == mapper['name']]
    if existing:
        mapper['id'] = existing[0]['id']
        kc('PUT', base + '/protocol-mappers/models/' + mapper['id'], mapper)
    else:
        kc('POST', base + '/protocol-mappers/models', mapper)

    def kv(path):
        try: return v('GET', 'finops/data/' + path)['data']['data']
        except RuntimeError as e:
            if '404' not in str(e): raise
            return {}

    data = kv('grafana')
    data['client_secret'] = kc('GET', base + '/client-secret')['value']
    data.setdefault('secret_key', secrets.token_hex(32))
    v('POST', 'finops/data/grafana', {'data': data})
    del data
    data = kv('postgres-exporter')
    data.setdefault('password', secrets.token_hex(32))
    v('POST', 'finops/data/postgres-exporter', {'data': data})
    password = data['password'].replace("'", "''")
    sql_admin("SET log_statement='none'; SET log_min_error_statement='panic'; "
              "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='finops_monitor') THEN "
              "CREATE ROLE finops_monitor LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION; END IF; END $$; "
              "ALTER ROLE finops_monitor PASSWORD '" + password + "' CONNECTION LIMIT 5; "
              "GRANT pg_monitor TO finops_monitor; GRANT CONNECT ON DATABASE finops TO finops_monitor; "
              "ALTER ROLE finops_monitor SET statement_timeout='10s';")
    del password, data
    for name, path, sa in [('finops-grafana', 'grafana', 'grafana'),
                           ('finops-postgres-exporter', 'postgres-exporter', 'postgres-exporter')]:
        v('PUT', 'sys/policies/acl/' + name, {'policy': 'path "finops/data/' + path + '" { capabilities = ["read"] }'})
        v('POST', 'auth/kubernetes/role/' + name, {
            'bound_service_account_names': [sa], 'bound_service_account_namespaces': ['monitoring'],
            'audience': 'vault', 'token_policies': [name], 'token_ttl': '15m', 'token_max_ttl': '30m',
        })
    print('Grafana client, explicit mikhail role, Vault workload policies and PostgreSQL monitor configured')
