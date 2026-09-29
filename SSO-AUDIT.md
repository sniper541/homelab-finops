# Central SSO audit — 2026-09-29

## Incident and verified cause

Keycloak logged `LOGIN_ERROR`, `username=admin`, `error=user_not_found` in realm `finops` for both `kafka-ui` and `finops-web`. The admin API confirms `admin` exists in `master`, while the human account in `finops` is `mikhail`. It is enabled, has a password credential, no required actions and no brute-force lock. No password was reset. A password credential's existence does not verify that the password being entered is correct.

Use `mikhail` and its existing password for application SSO. Use `master/admin` only for Keycloak administration. Do not create a second application admin to conceal this mismatch.

## Authentication boundaries

| Service | Client | Callback | Method |
| --- | --- | --- | --- |
| Web | finops-web | https://app.sniper541.com/ | Public authorization code + PKCE S256 |
| Kafka UI | kafka-ui | https://kafka.sniper541.com/login/oauth2/code/keycloak | Confidential authorization code |
| Vault UI | vault | https://vault.sniper541.com/ui/vault/auth/oidc/oidc/callback | Confidential OIDC |

All use issuer `https://auth.sniper541.com/realms/finops`. Separate clients, exact callbacks, no password grants. Web holds tokens in adapter memory and attaches Bearer tokens to API requests. Its entry screen now offers Sign in; no credential form, iframe or cross-window callback bridge. Telegram remains a disabled placeholder.

The browser flow includes Cookie authentication. Neither Web, Kafka UI nor the observed Vault request forces `prompt=login`. SSO reuses the Keycloak session; service sessions remain separate. Logging out of Keycloak does not necessarily revoke an already-issued Vault token or Kafka UI session immediately. Do not claim universal instantaneous logout.

`applications/keycloak/configure_sso.py` reconciles client metadata and restores self-only framing after the new Web has deployed. It preserves client secrets, users and unrelated attributes. Run through the authenticated operator helper; never store admin credentials in Git.

## Runtime checks

- Primary workloads ready; Argo applications observed healthy/synced before changes.
- App, API, Keycloak, Kafka UI and Vault TLS certificates Ready.
- Ingress routes point to their own services; no BasicAuth middleware in these routes.
- Keycloak hostname is canonical HTTPS, `KC_PROXY_HEADERS=xforwarded`, internal HTTP enabled behind Traefik.
- Browser-observed Keycloak authentication cookies are Secure; AUTH_SESSION_ID and KC_RESTART are HttpOnly. Kafka SESSION is Secure, HttpOnly, SameSite=Lax.
- Browser-observed Kafka UI and Vault authorization requests have the expected realm, client and callback. Both display the neutral “Единый вход” heading. Vault login has no app links.
- Kafka UI v1.5.0 uses OAuth2. Its injected client secret matches the live Keycloak secret (compared in memory, never printed). Its broker connection uses SCRAM-SHA-512.
- Kafka UI Vault template reads `finops/data/kafka` and `finops/data/kafka-ui`. Backend and consumer also obtain Kafka credentials via Vault; broker authentication remains SCRAM.
- API verifies RS256 signature, expiry, issuer, audience `finops-api` and UUID subject, then resolves an active linked user. Requests without a Bearer token return 401. Client-selected `user_id` is rejected. There is no independent password login.
- The `finops-api-access` mapper puts the API audience only into access tokens, not ID tokens.
- `mikhail` has the explicit `vault/vault-admin` role. Vault is unsealed and its public health endpoint returns 200.
- Recent Web/API/Traefik log sample contained no errors; Keycloak errors matched the wrong-realm username incident. One Kafka UI warning was observed; not evidence of failed credentials.

## Remaining operator checks / secrets migration

At audit time Keycloak still references `keycloak-db-secret` and `keycloak-admin-secret` in Kubernetes. This does not meet the new application-secrets rule. Migration requires authenticated Vault administration to provision a dedicated policy/Kubernetes role and store existing DB credentials without exposing or rotating them. Do not delete these Secrets before a successful replacement rollout. The staged optimized Keycloak manifest is not the same as the upstream-image runtime; never apply it wholesale.

No reusable Vault administrative token exists in `~/.vault-token` at audit time. Full private Vault OIDC/role review and this migration remain pending that access. Kubernetes workload auth and human OIDC must stay independent. No unseal keys or root token are required for ordinary OIDC administration.

End-to-end production SSO with the existing human account still requires a user login: sign into Web as `mikhail`, then open Kafka UI and initiate Vault OIDC in the same browser. A fresh private window should request credentials once; later services should reuse the session. Check Web data loading and logout. Do not send passwords, tokens or unseal keys in chat.

## Reproducible checks

Node/npm do not need `.venv`. For manual file editing on the server use `vi`.

```sh
cd /home/sniper541/homelab-finops/applications/web
npm ci
npm test
npm run build
cd /home/sniper541/homelab-finops
python3 applications/keycloak/tests/test_sso_config.py
```

Web: 21 tests passed and production build succeeded locally. The SSO configuration check covers exact client callbacks, PKCE, repeat application, preserved secrets and self-only framing. Desktop/mobile browser checks found no credentials/iframes, horizontal overflow or enabled Telegram placeholder.

References: [Kafbat OAuth2 configuration](https://ui.docs.kafbat.io/configuration/authentication/for-the-ui/oauth2), [Keycloak JavaScript adapter](https://www.keycloak.org/securing-apps/javascript-adapter).
