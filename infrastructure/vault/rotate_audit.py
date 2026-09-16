"""Rotate persistent Vault audit at 64 MiB; keep fourteen compressed segments.

Run hourly as the Kubernetes operator. Renames, requests Vault reopen via SIGHUP,
then compresses the closed file. Never truncates the active audit file. No Vault
token is required. Disk usage still needs monitoring: one hour of unusually high
traffic may exceed the threshold before the next invocation.
"""
from datetime import datetime, timezone
import argparse
import re
import subprocess
import time

K = ["kubectl", "--kubeconfig=/home/sniper541/.kube/config", "-n", "vault", "exec", "vault-0", "--"]


def command(*args):
    return subprocess.check_output(K + list(args), text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Verify rotation below the size threshold")
    args = parser.parse_args()
    size = int(command("stat", "-c", "%s", "/vault/audit/audit.json"))
    if size < 64 * 1024 * 1024 and not args.force:
        print("Audit file below rotation threshold")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = "/vault/audit/audit-" + stamp + ".json"
    # Helm runs a wrapper shell as PID 1. Signal only the actual Vault server.
    processes = command("ps", "-o", "pid,comm,args")
    pids = re.findall(r"^\s*(\d+)\s+vault\s+vault server(?:\s|$)", processes, re.MULTILINE)
    if len(pids) != 1:
        raise RuntimeError("Cannot identify one Vault server; no log moved")
    command("mv", "-n", "/vault/audit/audit.json", archive)
    command("kill", "-HUP", pids[0])
    for _ in range(20):
        exists = subprocess.run(K + ["test", "-f", "/vault/audit/audit.json"], capture_output=True)
        if exists.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError("Audit reopen failed; original log retained in rotated segment")
    command("gzip", archive)
    files = command("find", "/vault/audit", "-maxdepth", "1", "-type", "f", "-name", "audit-*.json.gz").splitlines()
    files = sorted(path for path in files if re.fullmatch(r"/vault/audit/audit-\d{8}T\d{6}Z\.json\.gz", path))
    for path in files[:-14]:
        command("rm", "--", path)
    print("Audit rotated; fourteen compressed segments retained")


if __name__ == "__main__":
    main()
