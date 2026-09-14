FROM quay.io/keycloak/keycloak:26.7.3@sha256:29be7252db0a106f1cd2ac17b9a56ff2668073da645638a38b9fc67deeb2d6c4

# Only login resources are added. The stock admin/account themes and runtime stay intact.
COPY --chown=1000:0 themes/finops /opt/keycloak/themes/finops
USER 1000
