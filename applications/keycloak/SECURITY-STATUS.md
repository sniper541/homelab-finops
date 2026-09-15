# Keycloak image release gate (2026-09-15)

The latest official stable release is still [26.7.3](https://github.com/keycloak/keycloak/releases/tag/26.7.3).
The pinned image digest is `sha256:29be7252db0a106f1cd2ac17b9a56ff2668073da645638a38b9fc67deeb2d6c4`.
Do not publish or deploy the theme image until its HIGH/CRITICAL vulnerability gate passes.
No CVE exceptions or manual JAR replacements are configured.

## Confirmed upstream blocker

`io.netty.netty-handler-4.1.136.Final.jar` is present in the official image.
[CVE-2026-75595](https://github.com/advisories/GHSA-c4c3-7fpv-j4q5) is fixed in
4.1.137.Final / 4.2.17.Final. Wait for an official patched Keycloak release,
review its upgrade notes, update the version and digest, and rerun the image workflow.
Do not downgrade Keycloak or substitute individual dependencies to bypass this gate.

## Verified JDBC version mismatch

Trivy 0.74.0 reports the JDBC driver as `13.2.1` and flags CVE-2025-59250.
The actual file is `com.microsoft.sqlserver.mssql-jdbc-13.2.1.jre11.jar`.
Its SHA-256 is:

```text
2d137aa308c78932878952fe3624ea090ecfe644414b8b23e71a305f425698c5
```

This matches the bytes of the official
[Maven Central 13.2.1.jre11 artifact](https://repo.maven.apache.org/maven2/com/microsoft/sqlserver/mssql-jdbc/13.2.1.jre11/mssql-jdbc-13.2.1.jre11.jar).
The [reviewed advisory](https://github.com/advisories/GHSA-m494-w24q-6f7w) lists
13.2.1.jre11 as fixed, and the [Keycloak release POM](https://github.com/keycloak/keycloak/blob/26.7.3/pom.xml)
selects that exact variant. This finding is a scanner version-identification mismatch.
No suppression is necessary while the independent Netty release blocker remains;
recheck scanner metadata when upgrading the upstream image.

## Runtime hardening

The custom image now performs the official `kc.sh build` for PostgreSQL, health and
metrics during the Docker build. The deployment uses `start --optimized`, a read-only
root filesystem, and bounded writable volumes for `/opt/keycloak/data` and `/tmp`.
The smoke test runs that actual optimized image read-only against disposable PostgreSQL
and exercises native login, PKCE code exchange, refresh and logout. It uses no production data.

The bootstrap upstream image reference in the manifest is not the optimized theme
image. Do not activate the prepared Keycloak Argo application until CI has replaced
that reference with a successfully scanned immutable custom image. Back up the database
before a future Keycloak version upgrade and review the upstream migration notes.

The current work does not modify Keycloak Secrets or the active realm configuration.
