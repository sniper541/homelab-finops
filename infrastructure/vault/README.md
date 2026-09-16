# Stage 16 — Vault operations

## Deployment status

Implemented and verified on 2026-09-16; remaining acceptance items are listed below:

- An encrypted pre-change Raft snapshot was copied off-node and SHA256 verified.
- Vault OIDC administration now requires the dedicated Keycloak client role
  `vault/vault-admin`, assigned to the designated administrator `mikhail`.
- Database engine `database/` and role `finops-api` are configured. A disposable
  dynamic user passed connect/data access, denied DDL/migration-table access,
  renewal and revocation checks. Both backend replicas now use dynamic leases.
- Six backend file rotation/fail-closed tests passed.
- Neutral Sniper541 theme passed isolated and production Chrome OIDC, PKCE,
  invalid-password, refresh, logout and repeat-login checks.
- Canonical issuer is `https://auth.sniper541.com/realms/finops`.
- Helm hardening, projected JWTs and audit PVC are deployed. Vault restarted and
  unsealed with unchanged Shamir 5/3. Audit file mode is 0600 with HMAC protection.
- A regular FinOps user was denied Vault; a dedicated Vault administrator passed
  OIDC, policy/engine UI, logout, SSO relogin and mobile login checks.
- Cross-secret access and wrong ServiceAccount/namespace/audience/JWT were denied.
- Legacy bot secrets and ignored secret.yaml were already absent; TLS and
  PostgreSQL bootstrap secrets were retained. SSH proxy now pins the trusted key.
- `vault-init.txt` was removed after external-share confirmation and verified
  final off-node snapshot. Temporary browser identities and tokens were removed.
- Hourly audit rotation is prepared but awaits approval to run/install; it has
  not been represented as active. A real Telegram /start confirmation is pending.

## Ownership

Keep the existing Helm release `vault` in namespace `vault`. Runtime ownership is
Helm, reconciled from `values.yaml` with official chart version **0.34.1**. ArgoCD
application `vault` owns only `manifests/` (ingress and protected audit PVC).
Do not adopt the existing StatefulSet into a second controller or reinstall it.
Do not delete `data-vault-0`, initialize Vault again, or change Shamir keys.

Apply reviewed Helm values only after an off-node snapshot and confirmation that
the three required unseal shares are available. Review rendered manifests and
the existing release first. The StatefulSet uses OnDelete updates; a deliberate
pod restart requires manual unseal and causes a single-node Vault outage.
With Helm 4 use `--server-side=false`: Injector owns its dynamic webhook CA,
which otherwise conflicts with Helm SSA. Keep the chart at 0.34.1; if the chart
repository is unavailable, use the official hashicorp/vault-helm Git tag v0.34.1.
The separate audit PVC avoids changing immutable StatefulSet claim templates.

All Kubernetes commands must explicitly use
`kubectl --kubeconfig=/home/sniper541/.kube/config`.

## Identity and policies

Human flow: Browser → `auth.sniper541.com` → Keycloak realm `finops` →
the requesting FinOps or Vault application. The canonical issuer cutover is live.

`configure_oidc_access.py` reconciles a dedicated client role and `vault_roles`
ID-token claim. Vault binds both the claim and audience `vault`, with subject
`sub`, an exact UI callback, one-hour tokens and four-hour maximum lifetime.
Ordinary FinOps users must not receive this client role. Existing Vault tokens
are not automatically revoked by changing OIDC bindings; audit prior entities
and issued tokens during final security validation.

The homelab `vault-admin` policy is explicitly a trusted administrator policy,
not a restricted application user. It can change policies and read secrets.
The security boundary excludes ordinary FinOps browser users, not the designated
Vault administrator. Root tokens are bootstrap/emergency only.

Workload flow: projected Pod ServiceAccount JWT (audience `vault`) → Kubernetes
Auth → exact ServiceAccount and namespace binding → application policy.
`configure_workloads.py` must be deployed together with projected-token manifests;
changing audience before a compatible pod rollout can prevent new pod startup.
Backend policy reads only `database/creds/finops-api`; bot policy reads its two KV
paths. Default Vault policy supports self lookup/renewal, not other applications.

## PostgreSQL dynamic credentials

`configure_database.py` accepts authenticated Vault/SQL operator callables. It
creates `finops_runtime` with data-only privileges and a separate non-superuser
`vault_db_manager` with CREATEROLE and administration of the runtime role. The
initial manager password stays in memory and is rotated by Vault. Reruns preserve
the configured manager password and leases. Protect and audit this manager: it
is a privileged infrastructure identity, not an application identity.

Role `finops-api` issues credentials with 30-minute TTL and two-hour maximum.
Vault Agent continuously renews/renders an atomic JSON file. Backend reads it
for every new psycopg connection; there is no connection pool or environment
snapshot retaining expired credentials. Missing/invalid files fail closed.
Revocation disables login, terminates that user's sessions, and removes the role.
Vault unavailability prevents issuing new leases; do not fall back to bootstrap
credentials. Alert on Agent renewal failures before lease expiry.

`postgres-secret` remains PostgreSQL's bootstrap/admin source, not the final
backend runtime source. Alembic runs separately as an authorized migration
identity, never with the runtime lease. Schema owners must explicitly grant
needed permissions on future tables; migrations are not run automatically here.
Never replay historical migrations against production to test this integration.

## Audit and transport

Protected `vault-audit` PVC is mounted at `/vault/audit`; file audit is enabled
at `/vault/audit/audit.json` with `log_raw=false` and HMAC protection. The rotation
script and user systemd units are prepared: hourly size check, 64 MiB threshold,
fourteen compressed segments. Their execution/installation awaits explicit
approval after automatic review blocked SIGHUP/retention/linger changes. Until
then monitor disk utilization manually; never disable audit as a space workaround.

External traffic uses HTTPS through Traefik and cert-manager. The internal Vault
listener and current PostgreSQL connection use HTTP/plain PostgreSQL inside the
cluster. This is a documented single-node trust boundary, not end-to-end TLS.
NetworkPolicy must be validated with DNS, TokenReview, injector and ingress paths
before activation. No claim of enforced network isolation is made yet.

## Backup, restore and unseal

Run `snapshot.py DESTINATION.snap` on an off-node operator workstation. Supply a
short-lived token with `raft-backup` policy through its hidden prompt. The script
never overwrites an existing recovery point and prints a SHA256 for verification.
Store backups on encrypted storage with restricted OS access. Do not commit them.
A copy on the same VM/PVC is not disaster recovery. A regular backup schedule,
retention and restore drill remain to be completed.

Shamir configuration is five shares, threshold three. The user confirmed all five
shares are stored outside the VM. `vault-init.txt` was removed after final off-node
backup, successful OIDC validation and the planned restart/unseal. Do not put
shares in scripts, environment files or Git.
Use the interactive `vault operator unseal` prompt for each of three distinct
shares. Never append shares to commands. There is no automatic unseal mechanism.

Restore procedure (first rehearse in an isolated recovery environment):

1. Verify snapshot checksum and retrieve at least three original shares from
   their external custodians. Record the Vault/chart versions used for backup.
2. Provision isolated compatible Vault/Raft storage; never overwrite the live
   production PVC during a drill. Block workload access to the recovery instance.
3. Initialize/unseal the empty recovery cluster only as needed to authenticate
   a temporary recovery administrator; this step is not for an existing cluster.
4. Use `vault operator raft snapshot restore -force PATH.snap` only against the
   verified isolated destination when the snapshot seal differs. For a matching
   seal use ordinary restore. This overwrites destination Vault state.
5. Unseal restored state with the original snapshot's Shamir shares. Check
   storage status, policies, auth methods and audit destination permissions.
6. Reconcile external credentials carefully: a snapshot does not roll back
   PostgreSQL passwords or Keycloak client secrets. Validate/reconfigure the
   database manager connection through an authorized operator; revoke stale
   leases and issue fresh ones before reconnecting workloads.
7. Verify OIDC, application isolation and a fresh snapshot before any deliberate
   production cutover. Keep the former recovery point until validation finishes.

Single replica and local-path storage are not HA. Future stages: off-node
scheduled backups with restore drills, multi-node Raft and external KMS unseal.
