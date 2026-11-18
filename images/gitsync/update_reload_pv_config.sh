#!/bin/sh
#
# Run by git-sync after each sync that brings in a new commit. If the alarm config xml file in the
# checkout differs from the copy the alarm server is using, copy the new one over and tell the alarm
# server to reload.
#
# A non-zero exit makes git-sync log the failure and run this script again a few seconds later.
#
# Required settings:
#   GIT_SYNC_ROOT   Directory git-sync keeps the checkout in
#   PV_CONFIG_FILE  Name of the xml file under alarm-config/ to watch, e.g. cryo.xml
#   TOPIC_NAME      Name of the alarm config, e.g. CRYO

for setting in GIT_SYNC_ROOT PV_CONFIG_FILE TOPIC_NAME; do
    eval "value=\${$setting}"
    if [ -z "$value" ]; then
        echo "ERROR: $setting is not set"
        exit 1
    fi
done

SOURCE="${GIT_SYNC_ROOT}/nalms-deployment.git/alarm-config/${PV_CONFIG_FILE}"
DEST="/tmp/nalms/${PV_CONFIG_FILE}"
# Present from the time a new file is copied until the alarm server has been told about it, so that
# a failed send is tried again on the next run rather than being lost.
RESTART_PENDING="/tmp/restart-pending-${PV_CONFIG_FILE}"

if [ ! -f "$SOURCE" ]; then
    echo "ERROR: $SOURCE does not exist"
    exit 1
fi

if ! cmp -s "$SOURCE" "$DEST"; then
    echo "Copying $SOURCE to $DEST"
    if ! cp "$SOURCE" "$DEST"; then
        echo "ERROR: Copy failed, not sending restart message"
        exit 1
    fi
    touch "$RESTART_PENDING"
fi

[ -f "$RESTART_PENDING" ] || exit 0

echo "Sending restart message to Kafka"
if ! echo "command:/${TOPIC_NAME}#{\"user\": \"sidecar\", \"command\": \"restart\"}" | \
    kcat -P -t "${TOPIC_NAME}Command" -b nalms-kafka-bootstrap:9092 -K "#"; then
    echo "ERROR: Could not send restart message"
    exit 1
fi
rm -f "$RESTART_PENDING"

echo "All done at $(date)"
exit 0
