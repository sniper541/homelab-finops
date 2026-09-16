"""Reconcile policies and scoped Kubernetes roles through an authenticated v callable."""
from pathlib import Path


def configure(v):
    for name in ("finops-api", "finops-bot", "vault-admin"):
        policy = (Path(__file__).parent / "policies" / (name + ".hcl")).read_text()
        v("PUT", "sys/policies/acl/" + name, {"policy": policy})
    for name in ("finops-api", "finops-bot"):
        v("POST", "auth/kubernetes/role/" + name, {
            "bound_service_account_names": [name],
            "bound_service_account_namespaces": ["finops"],
            "audience": "vault", "token_policies": [name],
            "token_ttl": 3600, "token_max_ttl": 14400,
        })
    print("Workload roles restricted by service account, namespace and Vault audience")
