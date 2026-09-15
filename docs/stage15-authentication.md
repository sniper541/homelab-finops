# Stage 15: authentication and authorization

## Browser and API

The public SPA uses `finops-web`, Authorization Code + PKCE S256. Native Keycloak
forms live at `https://app.sniper541.com/auth/realms/finops/...`; React never handles
passwords. State/nonce, refresh and logout remain managed by keycloak-js. Tokens
exist only in memory. Reload uses the Keycloak SSO session. No password grant,
browser client secret or iframe login is used.

FastAPI accepts only RS256 JWTs signed by the configured realm JWKS. It requires
issuer `https://app.sniper541.com/auth/realms/finops`, `exp`, audience `finops-api`,
and a UUID `sub`. The JWKS URL uses the existing internal Keycloak service; no
private signing keys are shared. Unknown/unlinked/inactive users are denied (403).
Missing/invalid/expired/wrong-audience tokens receive 401 with a Bearer challenge.

Identity is `JWT sub -> users.keycloak_sub -> users.id`, never UUID equals BIGINT.
No email-based auto-linking is performed. The existing unique keycloak_sub index
is sufficient; no schema migration or duplicate index is introduced.

All category/transaction/report operations derive the internal user from the
verified session. Update/delete SQL includes both resource ID and owner in the
same statement. Transaction creation selects only an active category belonging
to that owner; the existing composite foreign key also enforces ownership.
Request bodies reject extra fields, and legacy user_id query parameters are
rejected. Public `/users/register` has been removed. An admin realm role never
bypasses ownership. `require_roles` checks active user membership and realm roles;
no artificial admin endpoint has been added.

## Telegram service boundary

The polling bot obtains client-credentials tokens as confidential client
`finops-bot`. Its sole API role is `finops-api/telegram-bot`. The backend requires
both that role and exact authorized party `azp=finops-bot` on `/bot/*` routes.
Browser JWTs cannot use these routes; service JWTs cannot use browser routes.

The service asserts `X-Telegram-User-ID` from `Update.effective_user.id`, received
via authenticated Telegram polling. It never trusts a browser-provided Telegram
identity or uses a cached internal ID to select another user. The API resolves
the Telegram ID into the same central `users` table and checks active membership.
Service compromise remains a trusted-boundary risk, like any identity-asserting
gateway: restrict the client role, protect/rotate its credential, and audit access.

Routes: POST `/bot/users/register`, GET `/bot/categories`, GET/POST
`/bot/transactions`, GET `/bot/reports/summary`. Bodies contain business fields
only. Unknown Telegram users must register through the service; inactive users
cannot re-register to reactivate themselves.

The client credential is in Kubernetes Secret `finops-bot-oidc`, key
`client-secret`, injected only into the bot container. It is never in Git or Web.
Client tokens are cached in memory and renewed with client_credentials before
expiration. Stage 16 Vault can replace the secret distribution/rotation mechanism
without changing the API contract.

## Realm and same-origin routing

`applications/keycloak/configure_realm.py` reconciles non-secret settings through
an authenticated Admin REST session. It creates an API audience client and a
default scope `finops-api-access` with an access-token-only audience mapper,
enforces PKCE on finops-web, configures the service account/role and temporary
brute-force lockouts. It does not change master credentials or realm roles.

The finops realm `attributes.frontendUrl` is the supported realm frontend URL
override, `https://app.sniper541.com/auth`. The server's existing hostname and
master/admin address remain `auth.sniper541.com`. Traefik strips `/auth` and routes
only `/auth/realms/finops` and `/auth/resources` to Keycloak. Admin and master are
not proxied through this application route. A separate Argo application manages
only this route manifest, excluding the blocked custom-image deployment.

Origin migration changes the issuer: existing browser tokens must be replaced
by signing in again. Do not add dual-issuer acceptance to hide the transition.
The read-only isolated PostgreSQL/Keycloak/proxy smoke test checks PKCE, audience,
new issuer, refresh, logout and unchanged master before cutover. Production smoke
uses temporary identities/data and removes them afterwards.

## Deliberately deferred

The custom Keycloak image/theme remains blocked by the upstream Netty CVE. The
active image is not replaced and no CVE gate is bypassed. See the Keycloak
SECURITY-STATUS.md for verified JDBC metadata false-positive evidence.

Self-registration and recovery remain disabled: SMTP/email verification and
anti-abuse onboarding policy must be ready first. Telegram browser login/linking
remains disabled. A future implementation must validate signed Telegram data,
freshness/replay, and require proof of both identities before linking; it must not
trust a browser telegram_id or create a second user database.

## Verification

Backend tests run against a disposable `finops_test` PostgreSQL database with real
RSA signatures and real SQL. Fixtures explicitly refuse a production database.
They cover claim validation, active/link checks, two-tenant ownership, malicious
identity fields, category ownership, service roles and Telegram registration.
Async httpx2 ASGI transport avoids the deprecated Starlette/httpx test adapter.
Web and bot tests verify token handling and client identity boundaries. Existing
Gitleaks/Trivy gates remain enforced; the published images still reach Kubernetes
through CI-generated image-SHA Git commits and ArgoCD.

Node/npm, Docker and Kubernetes do not need Python `.venv`. Use `vi` for manual edits.

References:
- https://www.keycloak.org/server/hostname
- https://www.keycloak.org/server/reverseproxy
- https://www.keycloak.org/docs/latest/server_admin/
- https://www.starlette.io/testclient/
