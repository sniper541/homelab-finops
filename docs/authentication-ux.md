# Authentication UX

New visitors use the adapter's normal `login-required` Authorization Code + PKCE
flow before React mounts. The only login form is the native Keycloak form under
`auth.sniper541.com`, styled as neutral Sniper541 SSO. React receives no passwords.
The same realm serves FinOps and Vault. See [Stage 16](stage16-vault-sso.md).

Callbacks (including errors) are processed without initiating a second flow.
An explicit logout records `finops.signed-out=true` in tab-local sessionStorage
before navigating to Keycloak logout. This is only a UX flag, never a token or
authorization claim. On return, adapter initialization has no automatic onLoad
action: the page displays "Вы вышли из аккаунта" and "Войти снова". The retry
button clears the marker and starts OIDC explicitly. Failed logout clears it too.
New tabs follow normal SSO. Access/refresh tokens remain exclusively in memory.

## Theme delivery without changing the runtime image

The 2026-09-15 check still finds upstream Netty CVE-2026-75595 in Keycloak 26.7.3.
The custom-image publication gate stays enforced. Branding is delivered separately
using Keycloak's supported `themes/finops` directory, mounted read-only from an
immutable, content-addressed Kubernetes ConfigMap. No init container, runtime
download, manual container edits, replacement JARs or changed image are involved.
This does NOT remediate the existing runtime CVE; its upstream upgrade remains due.

After tests and Security CI, the operator deploys the reviewed Git revision:

```sh
python3 applications/keycloak/deploy_theme.py --output /tmp/finops-theme-review
# Review configmap.json and deployment-patch.json before applying.
python3 applications/keycloak/deploy_theme.py --output /tmp/finops-theme-review --apply
kubectl --kubeconfig=/home/sniper541/.kube/config -n keycloak rollout status deployment/keycloak
```

Then set only the finops realm's loginTheme to `finops` through authenticated
Admin REST/console. Keep master/account themes unchanged. Use Russian as the
realm's default locale, retaining English as an alternative. No credentials
belong in this script, Git or generated manifests.

The active upstream Keycloak Deployment remains operator-managed. The script
uses a resourceVersion precondition and merges only its named volume/mount;
existing image, security contexts, args, secrets, probes and resources are retained.
Existing Argo applications continue managing API/Web/Bot and auth routing.
Do not activate the staged optimized-image Argo application before its image gate
passes. When adopting that deployment, the image already contains the theme:
remove this external mount as part of the reviewed migration, avoiding stale overrides.

Rollback: select the previous realm login theme, then revert the named volume's
ConfigMap reference to the previous immutable revision. Retain previous revisions
until rollout and browser smoke pass. A changed ConfigMap name triggers a rollout;
there are no mutable in-place theme updates hidden by Keycloak caches.

The login template derives from the Apache-2.0 Keycloak 26.7.3 base login template.
Native form action, errors, password visibility, autocomplete, conditional passkey
UI and hidden credential fields are retained; review upstream changes on upgrades.
Registration/recovery are rendered as unavailable when disabled in the realm.
Telegram login remains disabled. These controls never perform fake authentication.

Node/npm do not require Python `.venv`; use `vi` for manual edits.
