"""Bootstrap database engine with authenticated Vault and SQL operator callables.

sql_admin runs SQL via stdin as the existing PostgreSQL bootstrap administrator.
Never log its input: initial manager password exists only in memory and is then
rotated by Vault. Reruns preserve Vault's manager password and active leases.
"""
import secrets


def configure(v, sql_admin):
    sql_admin("""
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='finops_runtime') THEN
    CREATE ROLE finops_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;
GRANT CONNECT ON DATABASE finops TO finops_runtime;
GRANT USAGE ON SCHEMA public TO finops_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON users, categories, transactions, user_settings TO finops_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO finops_runtime;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
""")
    mounts = v("GET", "sys/mounts")["data"]
    if "database/" not in mounts:
        v("POST", "sys/mounts/database", {"type": "database"})
    try:
        config = v("GET", "database/config/finops-postgres")
    except RuntimeError as error:
        if "404" not in str(error):
            raise
        config = None
    if not config:
        password = secrets.token_hex(32)
        sql_admin("""
SET log_statement = 'none';
SET log_min_error_statement = 'panic';
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='vault_db_manager') THEN
    CREATE ROLE vault_db_manager LOGIN NOSUPERUSER NOCREATEDB CREATEROLE NOREPLICATION;
  END IF;
END $$;
ALTER ROLE vault_db_manager PASSWORD '""" + password + """';
GRANT finops_runtime TO vault_db_manager WITH ADMIN OPTION;
GRANT CONNECT ON DATABASE finops TO vault_db_manager;
""")
        v("POST", "database/config/finops-postgres", {
            "plugin_name": "postgresql-database-plugin",
            "allowed_roles": ["finops-api"],
            "connection_url": "postgresql://{{username}}:{{password}}@postgres.finops.svc.cluster.local:5432/finops?sslmode=disable",
            "username": "vault_db_manager", "password": password,
            "max_open_connections": 4, "max_idle_connections": 2,
        })
        del password
        v("POST", "database/rotate-root/finops-postgres", {})
    v("POST", "database/roles/finops-api", {
        "db_name": "finops-postgres", "default_ttl": "30m", "max_ttl": "2h",
        "creation_statements": [
            'CREATE ROLE "{{name}}" WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD \'{{password}}\' VALID UNTIL \'{{expiration}}\'; '
            'GRANT finops_runtime TO "{{name}}"; '
            'GRANT "{{name}}" TO vault_db_manager WITH INHERIT TRUE, SET TRUE;'
        ],
        "renew_statements": ['ALTER ROLE "{{name}}" VALID UNTIL \'{{expiration}}\';'],
        "revocation_statements": [
            'ALTER ROLE "{{name}}" NOLOGIN; '
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = '{{name}}'; "
            'DROP ROLE IF EXISTS "{{name}}";'
        ],
    })
    print("Database engine configured: restricted runtime role, 30m TTL / 2h maximum")
