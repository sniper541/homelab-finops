"""Download a Raft snapshot over HTTPS to an off-node destination.

Use a short-lived token with raft-backup policy; token input is hidden and never
persisted. Run on the operator workstation, not the Vault server. A snapshot
contains encrypted secrets: protect it with OS permissions and encrypted storage.
"""
import argparse
import getpass
import hashlib
import os
from pathlib import Path
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    token = getpass.getpass("Short-lived Vault backup token: ")
    request = urllib.request.Request(
        "https://vault.sniper541.com/v1/sys/storage/raft/snapshot",
        headers={"X-Vault-Token": token},
    )
    digest = hashlib.sha256()
    # Never overwrite an earlier recovery point.
    fd = os.open(args.destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as output, urllib.request.urlopen(request, timeout=60) as response:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        args.destination.unlink(missing_ok=True)
        raise RuntimeError("Snapshot failed; incomplete destination removed") from None
    print("Snapshot saved:", args.destination, "SHA256:", digest.hexdigest())


if __name__ == "__main__":
    main()
