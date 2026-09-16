# FinOps Web authentication

The browser uses `keycloak-js` with Authorization Code Flow (`standard`) and
PKCE `S256`: https://auth.sniper541.com, realm `finops`, public client `finops-web`.
No client secret is required. Access and refresh tokens remain in memory.
The adapter initializes once before React mounts. Login and logout redirect via
Keycloak and return to the current origin's `/`. A page reload checks the SSO session.
Before dashboard requests, the access token is refreshed if less than 30 seconds
remain. All three requests include `Authorization: Bearer <access token>`.

FastAPI verifies RS256, issuer, expiry, audience `finops-api` and subject, then maps
`sub` to an active internal user. The browser never supplies a user identity.
API failures are shown explicitly; no demonstration balances replace real data.

## Keycloak client

- Client authentication OFF; Standard flow ON; Direct access grants OFF.
- Valid redirect URI and post logout redirect URI: `https://app.sniper541.com/`.
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
requests with Bearer and no client-selected identity, session restoration after reload, refresh after
token expiry, and logout returning to the login screen. Do not copy tokens into logs.
For cross-origin API requests, the API must allow the app origin and Authorization
header in its CORS preflight response.

Adapter documentation: https://www.keycloak.org/securing-apps/javascript-adapter

## Welcome screen and registration

`AuthScreen.tsx` and `welcome.css` provide the responsive public welcome screen.
Login navigates to the native Keycloak form under the same public application
origin. React has no username/password inputs. Master/admin stay on the separate
administration host. Telegram is explicitly disabled until real linking is implemented.

Registration is off. First configure SMTP, email verification and anti-abuse controls.
After enabling **finops → Realm settings → Login →
User registration**, set the non-secret GitHub Actions repository variable
`FINOPS_REGISTRATION_ENABLED=true` and rerun Web CI. For local Vite, set
`VITE_REGISTRATION_ENABLED=true`. The enabled CTA calls `keycloak.register()`;
the flag alone does not enable registration on the server.

Theme build, initial ArgoCD adoption, realm settings and rollback:
[Keycloak theme instructions](../keycloak/README.md).
