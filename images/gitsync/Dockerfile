# Image for the git-sync sidecar that runs next to each alarm server. Published as tidacs/nalms-config-sync.
#
# It is git-sync plus kcat and a hook script. git-sync keeps a checkout of this repo up to date, and the hook
# copies a changed alarm config xml file to the alarm server and tells it to reload.

FROM alpine:3.24

RUN apk add --no-cache ca-certificates git kcat

# The git-sync binary is taken from the upstream image rather than being kept in this repo
COPY --from=registry.k8s.io/git-sync/git-sync:v3.6.4 /git-sync /git-sync
COPY update_reload_pv_config.sh /usr/bin/update_reload_pv_config.sh
COPY sparse-checkout /tmp/sparse-checkout

ENTRYPOINT ["/git-sync"]
