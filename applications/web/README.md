# FinOps Web authentication

The browser uses `keycloak-js` with Authorization Code Flow (`standard`) and
PKCE `S256`: https://auth.sniper541.com, realm `finops`, public client `finops-web`.
No client secret is required. Access and refresh tokens remain in memory.
The adapter initializes once before React mounts. Login and logout redirect via
Keycloak and return to the current origin's `/`. A page reload checks the SSO session.
Before dashboard requests, the access token is refreshed if less than 30 seconds
remain. All three requests include `Authorization: Bearer <access token>`.

`user_id=1` remains the temporary default (`VITE_USER_ID` override is preserved).
FastAPI does not yet validate JWTs: this change does not provide backend access
control or isolate users. JWT validation and deriving user identity on the backend
are the next step. API outage fallback remains; authentication failures do not use it.

## Keycloak client

- Client authentication OFF; Standard flow ON; Direct access grants OFF.
- Valid redirect URIs and post logout redirect URIs: `https://app.sniper541.com/*`.
- Web origins: `https://app.sniper541.com`.
- For local development, explicitly allow `http://localhost:5173/*` for both redirect
  settings and `http://localhost:5173` for Web origins.

## Checks

Node 22; Python `.venv` is not needed. For manual edits use `vi`.

```bash
cd /home/sniper541/homelab-finops/applications/web
npm ci
npm test
npm run build
```

After deploying, check login in a private window, `response_type=code` and
`code_challenge_method=S256` in the authorization request, successful dashboard
requests with Bearer and `user_id=1`, session restoration after reload, refresh after
token expiry, and logout returning to the login screen. Do not copy tokens into logs.
For cross-origin API requests, the API must allow the app origin and Authorization
header in its CORS preflight response.

Adapter documentation: https://www.keycloak.org/securing-apps/javascript-adapter
