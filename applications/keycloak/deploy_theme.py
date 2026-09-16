"""Render/apply an immutable read-only theme volume without replacing the IAM image.

Run only reviewed sources after theme smoke and repository security checks.
Uses the operator's kubectl context; no credentials are read or written here.
The active upstream Deployment is currently operator-managed, not the staged
optimized-image Argo application. Do not apply that staged Deployment here.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess


def manifests():
    root = pathlib.Path(__file__).parent / "themes" / "finops"
    files = sorted(p for p in root.rglob("*") if p.is_file())
    data = {f"asset-{i}": p.read_text(encoding="utf-8") for i, p in enumerate(files)}
    items = [{"key": f"asset-{i}", "path": p.relative_to(root).as_posix()} for i, p in enumerate(files)]
    digest = hashlib.sha256(json.dumps([data, items], sort_keys=True).encode()).hexdigest()[:16]
    name = "finops-login-theme-" + digest
    config = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": name, "namespace": "keycloak",
              "labels": {"app.kubernetes.io/part-of": "finops", "app.kubernetes.io/component": "login-theme"}},
              "immutable": True, "data": data}
    patch = {"spec": {"template": {"spec": {
        "volumes": [{"name": "finops-login-theme", "configMap": {"name": name, "defaultMode": 292, "items": items}}],
        "containers": [{"name": "keycloak", "volumeMounts": [{"name": "finops-login-theme",
            "mountPath": "/opt/keycloak/themes/finops", "readOnly": True}]}]}}}}
    return config, patch


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--kubeconfig", default="/home/sniper541/.kube/config")
    args = parser.parse_args()
    config, patch = manifests()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in (("configmap.json", config), ("deployment-patch.json", patch)):
        (args.output / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Theme revision:", config["metadata"]["name"])
    if args.apply:
        cmd = ["kubectl", "--kubeconfig=" + args.kubeconfig, "-n", "keycloak"]
        live = json.loads(subprocess.check_output(cmd + ["get", "deployment", "keycloak", "-o", "json"]))
        image = next(c["image"] for c in live["spec"]["template"]["spec"]["containers"] if c["name"] == "keycloak")
        patch["metadata"] = {"resourceVersion": live["metadata"]["resourceVersion"]}
        subprocess.run(cmd + ["apply", "-f", str(args.output / "configmap.json")], check=True)
        subprocess.run(cmd + ["patch", "deployment", "keycloak", "--type=strategic", "-p", json.dumps(patch)], check=True)
        after = json.loads(subprocess.check_output(cmd + ["get", "deployment", "keycloak", "-o", "json"]))
        assert next(c["image"] for c in after["spec"]["template"]["spec"]["containers"] if c["name"] == "keycloak") == image
        print("Only the theme volume changed; runtime image retained. Select loginTheme=finops after rollout.")
