# FinOps Platform observability

Grafana is a standalone ArgoCD application at https://grafana.sniper541.com.
The maintained `grafana-community/grafana` chart is pinned to 13.2.7,
Grafana to 13.2.3. Prometheus remains in kube-prometheus-stack 91.9.0.
Persistent resources are reconciled from this directory and the ArgoCD
application manifests in `../argocd`.

## Authentication and secret rotation

Grafana uses the `grafana` confidential Keycloak client in realm `finops`.
The callback is `/login/generic_oauth`; code flow requires PKCE S256.
Refresh tokens and automatic SSO login are enabled. Local login, Basic Auth,
anonymous access and initial local administrator creation are disabled.
The `grafana_roles` claim maps the explicitly assigned realm role
`grafana-admin` to GrafanaAdmin. Other authenticated users receive Viewer.
`mikhail` has the administrator role. Role synchronization remains enabled.

Vault KV v2 paths and Kubernetes identities:

| Path | Policy / Kubernetes role | ServiceAccount / namespace |
| --- | --- | --- |
| `finops/data/grafana` | `finops-grafana` | `grafana` / `monitoring` |
| `finops/data/postgres-exporter` | `finops-postgres-exporter` | `postgres-exporter` / `monitoring` |

The injector authenticates with a projected token whose audience is `vault`.
Its init container writes mode-0400 files, owned by the workload UID.
Grafana reads its OAuth client secret and encryption key through file providers.
The exporter uses `DATA_SOURCE_PASS_FILE`. No OAuth credential is rendered into
a ConfigMap, Helm value or Kubernetes Secret. The TLS certificate remains a
cert-manager-managed Kubernetes Secret.

`configure_access.py` documents the idempotent operator reconciliation. It needs
authenticated, in-memory Keycloak/Vault callables and a local PostgreSQL admin
connection; it contains no credential. Repeated execution preserves existing
Grafana encryption and exporter keys. Rotate the OAuth secret in Keycloak and
Vault together, then restart Grafana. Rotate the PostgreSQL monitoring password
in PostgreSQL and Vault together, then restart its exporter. Init-only injection
does not automatically reload changed secrets. Keep Grafana's encryption key
stable alongside its PVC; replacing it makes stored encrypted data unreadable.

The PostgreSQL `finops_monitor` role is limited to `pg_monitor`, five connections,
and a ten-second statement timeout. The exporter does not collect SQL statements.

## Metrics and dashboards

API metrics use a separate internal listener on port 9001. The public Service
still exposes only the existing API port. HTTP labels contain route templates,
bounded methods and status codes, never raw URLs, user IDs or request bodies.
Health probes are excluded. One uvicorn process runs per pod; a future
multi-worker configuration must use Prometheus multiprocess collectors.

Traefik's existing Prometheus endpoint covers edge traffic, so no additional
Nginx exporter is installed. Strimzi supplies JMX metrics and Kafka exporter.
The Kafka Argo application intentionally has automatic pruning disabled to
protect the existing Kafka CR, node pool, users, topics and storage.

Six dashboards are provisioned in **FinOps Platform**. Platform Overview is home.
Edit `build_dashboards.py`, regenerate JSON, and commit both:

```sh
python3 infrastructure/observability/build_dashboards.py
python3 infrastructure/observability/check_dashboards.py http://PROMETHEUS:9090
```

The checker executes every PromQL expression against a real Prometheus and
fails on invalid queries or missing infrastructure data. It separately reports
idle HTTP metrics and partitions with no committed consumer offset. An idle
latency histogram has no quantile; it must not be presented as zero latency.
Transaction panels count HTTP submission outcomes, not downstream settlement.
Kafka offset `-1` means no committed offset. Kafka remains a single broker,
replication factor 1, with no high availability.

The default kube-prometheus-stack rules cover node CPU, filesystem capacity,
CrashLoop and deployment availability. `resources/alerts.yaml` adds API,
PostgreSQL, Kafka, workload scrape and memory-pressure rules. API latency and
error alerts require meaningful request volume. Notification delivery is not
configured; Alertmanager can receive a real notification route in a later stage.

## Operations

Use `kubectl --kubeconfig=/home/sniper541/.kube/config` on the server.
Check Argo application health, pod readiness, PVC binding, TLS validity and
Prometheus targets after changes. Allow up to ten minutes for initial Grafana
migrations; normal restarts should be much faster.

The Grafana PVC is 2 GiB on local-path. This is persistence, not an off-node
backup or high availability. Back up the PVC together with its Vault encryption
key before upgrades or host recovery.

Review VM memory before Stage 18.3. An 8-GiB node has limited headroom for the
existing platform plus Prometheus and Grafana; 16 GiB is recommended before
adding Loki/Alloy. Neither Loki nor Alloy is installed by this stage.
