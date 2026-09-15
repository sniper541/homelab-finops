# FinOps login theme

Only `themes/finops/login` is installed. The theme inherits `keycloak` from
Keycloak **26.7.3**. Stock login, registration, recovery, MFA and validation
templates remain in use. Custom CSS, a local SVG, message bundles and a small
footer make the pages consistent with the Web welcome screen. There are no
external fonts, scripts, passwords or admin credentials in this image.

The base image is pinned to the verified 26.7.3 digest. The Docker build prepares
PostgreSQL, health and metrics support for `start --optimized`. The root filesystem
is read-only; bounded volumes provide writable data and temporary directories.
PostgreSQL connection and Secret references are unchanged. See
[SECURITY-STATUS.md](SECURITY-STATUS.md) for the upstream CVE publication blocker.

## Validate without production changes

Node/npm, Docker and Kubernetes do not need Python `.venv`. Manual editing: `vi`.

```bash
cd /home/sniper541/homelab-finops
docker build -t finops-keycloak:test applications/keycloak
python3 applications/keycloak/tests/smoke.py --image finops-keycloak:test
```

The smoke test creates a disposable PostgreSQL instance and realm with a generated test user and no admin credentials, and
binds a random loopback port. It exercises actual login/registration/recovery
pages, invalid-login validation, assets and the unchanged master theme, then verifies
Authorization Code + PKCE token exchange, refresh and logout with that test user. It removes
both containers, their Docker network and fixture on exit. `--keep --port 18080` is for manual visual QA;
remove the printed container, its `-db` companion, same-name network and fixture afterwards. It never connects to the
production PostgreSQL database. The test password is generated at runtime, used only
in the disposable native Keycloak form, never printed or committed, and deleted with
the fixture. There is no password grant. `--existing-origin` only accepts a loopback
QA instance and runs page checks without generating a second account/session.

## Publication and GitOps

`Keycloak theme CI` builds, smoke-tests and scans before publishing to
`ghcr.io/sniper541/homelab-finops/finops-keycloak:sha-<full-commit>`.
It never uses `latest`, never overwrites an existing SHA tag, and records the tag
**and registry digest** in `infrastructure/keycloak/deployment.yaml`.
Reruns reuse an existing tag. Trivy blocks publication/promotion on fixable
HIGH/CRITICAL findings; do not bypass this gate just to publish the theme.
The workflow also uploads a CycloneDX SBOM. It uses only the repository's standard
`GITHUB_TOKEN` for GHCR/Git, not Keycloak credentials.

The checked-in Deployment retains an upstream bootstrap image reference until
the first successful pipeline replaces it with the optimized custom image.
Do not apply this deployment or activate the Keycloak Argo application while the
bootstrap reference remains: `--optimized` requires the prepared custom image.
Do not invent a SHA or deploy an unpublished image.

1. Review and commit the explicit file list in the handoff. Push when ready.
2. Ensure Actions has read/write contents and packages permissions. Wait for
   `Keycloak theme CI` and the Web workflow to pass, including their manifest commits.
3. In GitHub Packages make `finops-keycloak` public (like the existing public app
   images), or provision a GHCR pull secret separately in the cluster. Do not put
   credentials in Git. A private package will otherwise produce ImagePullBackOff.
4. Pull the CI manifest commit and verify its `sha-...@sha256:...` image reference.
5. Bootstrap the new ArgoCD Application once, with your working Kubernetes context:

   ```bash
   git pull --rebase origin main
   git diff -- infrastructure/keycloak/deployment.yaml
   grep 'image:' infrastructure/keycloak/deployment.yaml
   kubectl apply -f infrastructure/argocd/finops-keycloak.yaml
   kubectl rollout status deployment/keycloak -n keycloak --timeout=300s
   ```

   On this host a bare `kubectl` may not read `/etc/rancher/k3s/k3s.yaml`; use the
   same authorized kubeconfig/sudo invocation you normally use. Do not change file
   permissions on kubeconfig for this task. Verify no other Argo Application already
   manages these resources before bootstrapping. This Application manages only the
   three explicit manifests and uses self-heal, with pruning off for initial adoption.
6. Only after the custom image is healthy, select the theme as described below.

## Realm settings (only finops)

Keycloak Admin Console → select **finops** → Realm settings → Themes →
**Login theme = finops** → Save.

Leave Account theme, Admin console theme, Email theme and the **master** realm
unchanged. Keeping the stock templates preserves Keycloak's security mechanisms.
If English is selected, labels are localized. For Russian, enable internationalization
under Localization, include `ru` and `en`, and choose `ru` as default if desired.

### Registration and recovery

The live login page inspected for this change had no registration/recovery links.
The Web's registration CTA is therefore gated off by default; its tab explains that
registration is closed. Telegram is disabled with a visible “Скоро” label.

To enable real registration:

1. **finops → Realm settings → Login → User registration = ON → Save.**
2. Verify the registration link on the Keycloak login page works.
3. Set GitHub repository **Settings → Secrets and variables → Actions → Variables →
   FINOPS_REGISTRATION_ENABLED = true**. This is a non-secret UI flag.
4. Run **Web CI → Run workflow** to rebuild both Vite and the Web image with the flag.

The CTA uses `keycloak.register()` with the same public client and PKCE settings.
The flag does not change realm policy. If registration is disabled again, set it to
`false` and rebuild Web. No user credentials are collected in React.

For password recovery, enable **Login → Forgot password**, and configure working
SMTP in **Realm settings → Email** through the admin UI. Do not put SMTP credentials
in this repository. Email delivery is not tested by the isolated smoke test.

## Browser checks after deployment

- Private window: full FinOps welcome screen; Telegram visibly unavailable.
- Login redirects to `auth.sniper541.com`, themed form uses the same palette/logo.
- Authorization request: `response_type=code`, `code_challenge_method=S256`.
- Correct account login returns to dashboard; reload, access-token refresh and
  logout still work. API requests retain Bearer and temporary `user_id=1`.
- Incorrect credentials show a readable error. Check keyboard focus, show-password,
  registration/recovery (when enabled), and mobile widths 320/390 px.
- Verify master/admin console remains stock. Never include real tokens in screenshots.

Rollback theme selection: **finops → Themes → Login theme = keycloak** (or the prior
selection) → Save. Roll back the image only after selecting an available stock theme,
then revert the image manifest through GitOps.

References: https://www.keycloak.org/ui-customization/themes and
https://www.keycloak.org/server/containers
