# git-sync sidecar image

Source for the `tidacs/nalms-config-sync` image, which runs as the `git-sync` sidecar container in each
alarm server StatefulSet (see `base/phoebus-alrm-srv-*.yaml`).

## What it does

- [git-sync](https://github.com/kubernetes/git-sync) keeps a checkout of this repository's `main` branch up to
  date inside the pod. `sparse-checkout` limits the checkout to the xml files directly under `alarm-config/`.
- After each sync that brings in a new commit, git-sync runs `update_reload_pv_config.sh`. The script compares
  `alarm-config/$PV_CONFIG_FILE` from the checkout with the copy the alarm server is using in `/tmp/nalms`. If they
  differ, it copies the new file over and sends a `restart` command to the `${TOPIC_NAME}Command` Kafka topic.
- The alarm server reloads its configuration when it receives that command and the file has changed.

The end result is that a change to `alarm-config/cryo.xml` or `alarm-config/lcls.xml` on `main` is picked up by the matching
alarm server a few minutes later, with no manual step.

If the script cannot copy the file or cannot send the restart command, it exits with an error. git-sync logs
the failure and runs the script again a few seconds later, and keeps doing so until it succeeds. A restart
command that could not be sent is not lost: the script remembers that one is owed and sends it on a later run.

## Settings

These are set on the sidecar container in the StatefulSet:

| Variable | Purpose |
|---|---|
| `GIT_SYNC_ROOT` | Where git-sync keeps the checkout. The script reads the xml from here. |
| `PV_CONFIG_FILE` | Name of the xml file under `alarm-config/` to watch, for example `cryo.xml`. |
| `TOPIC_NAME` | Alarm config name, for example `CRYO`. The restart goes to `<TOPIC_NAME>Command`. |

How often git-sync checks for new commits is set by the `--wait` argument, in seconds. This version of
git-sync (v3) does not read `GIT_SYNC_PERIOD`, and without `--wait` it checks every second.

The repository name (`nalms-deployment.git`), the `alarm-config/` path and the Kafka bootstrap address
(`nalms-kafka-bootstrap:9092`) are fixed in the script.

## Building

```sh
docker build -t tidacs/nalms-config-sync:<X.Y.Z> images/gitsync
docker push tidacs/nalms-config-sync:<X.Y.Z>
```

Then update the image tag in `base/phoebus-alrm-srv-*.yaml`. Rolling the pods restarts the alarm servers.
