"""Test the optimized read-only image with disposable PostgreSQL; no production credentials."""
import argparse
import html
import base64
import hashlib
import http.cookiejar
import json
import pathlib
import re
import socket
import secrets
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--image", default="finops-keycloak:test")
parser.add_argument("--theme-dir", type=pathlib.Path, help="Mount reviewed theme files read-only, independently of the image")
parser.add_argument("--keep", action="store_true", help="Keep loopback-only test container for visual QA")
parser.add_argument("--port", type=int, default=0)
parser.add_argument("--existing-origin", help="Reuse a disposable QA container already started by this script")
parser.add_argument("--public-prefix", default="", help="Test a reverse-proxied realm frontend URL, e.g. /auth")
args = parser.parse_args()
name = f"finops-theme-smoke-{int(time.time())}"
db_name = name + "-db"
db_password = secrets.token_urlsafe(32)
with socket.socket() as sock:
    sock.bind(("127.0.0.1", args.port))
    port = sock.getsockname()[1]
origin = args.existing_origin or f"http://127.0.0.1:{port}"
direct_origin = origin
if args.public_prefix:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        backend_port = sock.getsockname()[1]
    direct_origin = f"http://127.0.0.1:{backend_port}"
    origin += args.public_prefix
assert urllib.parse.urlparse(origin).hostname in ("127.0.0.1", "localhost"), "Only disposable loopback instances are allowed"
fixture_dir = pathlib.Path(tempfile.mkdtemp(prefix="finops-theme-test-"))
fixture = fixture_dir / "realm.json"
test_password = secrets.token_urlsafe(32)
fixture.write_text(json.dumps({
    "realm": "finops", "enabled": True, "loginTheme": "finops",
    "browserSecurityHeaders": {"contentSecurityPolicy": "frame-src 'self'; frame-ancestors 'self' http://localhost:5173; object-src 'none';", "xFrameOptions": ""},
    "attributes": {"frontendUrl": origin} if args.public_prefix else {},
    "registrationAllowed": True, "resetPasswordAllowed": True,
    "internationalizationEnabled": True, "supportedLocales": ["ru", "en"], "defaultLocale": "ru",
    "users": [{"username": "theme-smoke-user", "enabled": True, "firstName": "Theme", "lastName": "Test",
        "email": "theme-test@example.invalid", "emailVerified": True,
        "credentials": [{"type": "password", "value": test_password, "temporary": False}]}],
    "clients": [{"clientId": "finops-web", "enabled": True, "publicClient": True,
        "standardFlowEnabled": True, "directAccessGrantsEnabled": False,
        "redirectUris": ["http://localhost:5173/*", origin + "/*"],
        "protocolMappers": [{"name":"api-audience","protocol":"openid-connect","protocolMapper":"oidc-audience-mapper",
            "config":{"included.custom.audience":"finops-api","access.token.claim":"true","id.token.claim":"false"}}],
        "webOrigins": ["http://localhost:5173", origin],
        "attributes": {"pkce.code.challenge.method": "S256", "post.logout.redirect.uris": "+"}}]
}), encoding="utf-8")
fixture.chmod(0o644)
class LoopbackCookiePolicy(http.cookiejar.DefaultCookiePolicy):
    def return_ok_secure(self, cookie, request):
        # Browsers treat localhost as a secure context; urllib otherwise drops these cookies.
        return urllib.parse.urlparse(request.full_url).hostname in ("127.0.0.1", "localhost") or super().return_ok_secure(cookie, request)

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar(LoopbackCookiePolicy())))

def page(url, data=None):
    with opener.open(url, data=data, timeout=10) as response:
        return response.read().decode("utf-8")

def themed(body):
    assert "css/finops.css" in body, "Custom stylesheet is missing"
    assert 'class="finops-footer"' in body, "Shared footer did not render"
    assert "Sniper541" in body

def link(body, fragment):
    candidates = re.findall(r'href="([^"]+)"', body)
    return urllib.parse.urljoin(origin, html.unescape(next(u for u in candidates if fragment in u)))

try:
    if not args.existing_origin:
        subprocess.run(["docker", "network", "create", name], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["docker", "run", "-d", "--name", db_name, "--network", name,
            "--memory=256m", "--cpus=1", "--tmpfs", "/var/lib/postgresql/data",
            "-e", "POSTGRES_DB=keycloak", "-e", "POSTGRES_USER=keycloak",
            "-e", "POSTGRES_PASSWORD=" + db_password, "postgres:17-alpine"], check=True, stdout=subprocess.DEVNULL)
        for attempt in range(60):
            ready = subprocess.run(["docker", "exec", db_name, "pg_isready", "-U", "keycloak"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Disposable PostgreSQL failed to start")
        subprocess.run(["docker", "run", "-d", "--name", name, "--memory=768m", "--cpus=1",
            "--security-opt=no-new-privileges", "--cap-drop=ALL",
            "--read-only", "--tmpfs", "/tmp:uid=1000,gid=0,mode=1777,size=128m",
            "--tmpfs", "/opt/keycloak/data:uid=1000,gid=0,mode=0770,size=256m",
            "--network", name, "-e", "KC_DB=postgres",
            "-e", f"KC_DB_URL=jdbc:postgresql://{db_name}:5432/keycloak",
            "-e", "KC_DB_USERNAME=keycloak", "-e", "KC_DB_PASSWORD=" + db_password,
            "-p", f"127.0.0.1:{backend_port if args.public_prefix else port}:8080", "-v", f"{fixture}:/opt/keycloak/data/import/realm.json:ro",
            *(["-v", f"{args.theme_dir.resolve()}:/opt/keycloak/themes/finops:ro"] if args.theme_dir else []),
            args.image, "start", "--optimized", "--import-realm", "--http-enabled=true",
            "--hostname=" + direct_origin, "--http-port=8080"], check=True, stdout=subprocess.DEVNULL)
        if args.public_prefix:
            config = fixture_dir / "nginx.conf"
            config.write_text('events {}\nhttp { server { listen 8080; location ' + args.public_prefix + '/ { '
                + 'proxy_pass http://' + name + ':8080/; proxy_set_header Host $http_host; '
                + 'proxy_set_header X-Forwarded-Proto http; proxy_set_header X-Forwarded-Host $http_host; } } }')
            config.chmod(0o644)
            subprocess.run(["docker","run","-d","--name",name+"-proxy","--network",name,
                "-p",f"127.0.0.1:{port}:8080","--memory=128m","--cpus=0.5",
                "-v",f"{config}:/etc/nginx/nginx.conf:ro","nginx:1.30.4-alpine"],check=True,stdout=subprocess.DEVNULL)
    deadline = time.monotonic() + 600
    while True:
        try:
            page(origin + "/realms/finops/.well-known/openid-configuration")
            break
        except Exception:
            if time.monotonic() >= deadline:
                raise RuntimeError("Disposable Keycloak failed to start within 600 seconds")
            time.sleep(2)
    params = urllib.parse.urlencode({"client_id": "finops-web", "redirect_uri": origin + "/",
        "response_type": "code", "scope": "openid", "kc_locale": "ru",
        "code_challenge": "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG", "code_challenge_method": "S256"})
    auth_url = origin + "/realms/finops/protocol/openid-connect/auth?" + params
    login = page(auth_url)
    themed(login)
    assert 'name="username"' in login and 'name="password"' in login
    css_url = link(login, "css/finops.css")
    assert "--finops-bg" in page(css_url)
    registration_url = link(login, "registration")
    recovery_url = link(login, "reset-credentials")
    registration = page(registration_url)
    themed(registration)
    assert 'name="password"' in registration and 'name="email"' in registration
    recovery = page(recovery_url)
    themed(recovery)
    assert 'name="username"' in recovery
    # A fresh auth session checks the real server-rendered validation error.
    login = page(auth_url)
    action = html.unescape(re.search(r'<form[^>]+action="([^"]+)"', login)[1])
    error_page = page(action, urllib.parse.urlencode({"username": "nonexistent-theme-test", "password": "invalid-test-input"}).encode())
    themed(error_page)
    assert 'aria-invalid="true"' in error_page or 'id="input-error"' in error_page
    # The stock master theme must not inherit FinOps resources.
    master = page(direct_origin + "/realms/master/protocol/openid-connect/auth?" + urllib.parse.urlencode({
        "client_id": "account-console", "redirect_uri": direct_origin + "/realms/master/account/",
        "response_type": "code", "scope": "openid", "code_challenge": "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG", "code_challenge_method": "S256"}))
    assert "css/finops.css" not in master
    checks = ["login", "registration", "recovery", "invalid-login error", "theme assets", "master unchanged"]
    if not args.existing_origin:
        # Complete the browser flow for an ephemeral, generated test account.
        # Credentials are posted only to Keycloak's native form, never a password grant.
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        flow_params = urllib.parse.parse_qs(params)
        flow_params.update(code_challenge=[challenge], response_mode=["query"])
        flow_url = origin + "/realms/finops/protocol/openid-connect/auth?" + urllib.parse.urlencode(flow_params, doseq=True)
        login_page = page(flow_url)
        action = html.unescape(re.search(r'<form[^>]+action="([^"]+)"', login_page)[1])
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        no_redirect = urllib.request.build_opener(NoRedirect(), next(h for h in opener.handlers if isinstance(h, urllib.request.HTTPCookieProcessor)))
        try:
            no_redirect.open(action, data=urllib.parse.urlencode({"username": "theme-smoke-user", "password": test_password}).encode(), timeout=10)
            raise AssertionError("Expected code redirect")
        except urllib.error.HTTPError as response:
            assert response.code == 302
            code = urllib.parse.parse_qs(urllib.parse.urlparse(response.headers["Location"]).query)["code"][0]
        token_url = origin + "/realms/finops/protocol/openid-connect/token"
        tokens = json.loads(page(token_url, urllib.parse.urlencode({"grant_type": "authorization_code", "client_id": "finops-web",
            "code": code, "code_verifier": verifier, "redirect_uri": origin + "/"}).encode()))
        assert tokens.get("access_token") and tokens.get("refresh_token") and tokens.get("id_token")
        payload_segment = tokens["access_token"].split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload_segment + "=" * (-len(payload_segment) % 4)))
        assert claims["iss"] == origin + "/realms/finops"
        assert claims["aud"] == "finops-api" or "finops-api" in claims["aud"]
        refreshed = json.loads(page(token_url, urllib.parse.urlencode({"grant_type": "refresh_token", "client_id": "finops-web",
            "refresh_token": tokens["refresh_token"]}).encode()))
        assert refreshed.get("access_token")
        logout_url = origin + "/realms/finops/protocol/openid-connect/logout?" + urllib.parse.urlencode({
            "id_token_hint": tokens["id_token"], "post_logout_redirect_uri": origin + "/"})
        try:
            no_redirect.open(logout_url, timeout=10)
            raise AssertionError("Expected logout redirect")
        except urllib.error.HTTPError as response:
            assert response.code == 302 and response.headers["Location"] == origin + "/"
        themed(page(flow_url))
        checks.extend(["authorization code + PKCE exchange", "access token", "refresh token", "logout"])
    print(json.dumps({"status": "passed", "checks": checks,
        "container": name, "origin": origin, "authorization_url": auth_url}, ensure_ascii=False), flush=True)
finally:
    if not args.keep or args.existing_origin:
        if not args.existing_origin:
            subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["docker", "rm", "-f", db_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["docker", "rm", "-f", name+"-proxy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["docker", "network", "rm", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (fixture_dir / "nginx.conf").unlink(missing_ok=True)
        fixture.unlink(missing_ok=True)
        fixture_dir.rmdir()
    else:
        print(f"QA container: {name}; fixture: {fixture_dir}; port: {port}", flush=True)
