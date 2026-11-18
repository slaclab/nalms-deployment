# Operations

How the deployment fits together and how to change it. For editing alarm configurations, see
[Editing alarm configurations](editing-alarms.md).

## How the pieces fit

Everything runs in the `nalms-dev` namespace.

- **Kafka**, managed by the Strimzi operator, carries the alarm topics. Each alarm configuration
  has a topic named after it (for example `CRYO`) plus `<name>Command` and `<name>Talk`.
- **A Phoebus alarm server** per configuration monitors the PVs and publishes alarm state to
  Kafka. Only CRYO is deployed at the moment.
- **A git-sync sidecar** in the alarm server pod checks this repository's `main` branch every
  two minutes. When `alarm-config/<name>.xml` changes, it copies the file into the pod and
  sends a `restart` command on the `<name>Command` topic. The alarm server then reloads. See
  [images/gitsync](../images/gitsync/README.md).
- **The alarm logger** forwards alarm messages to Loki.
- **The alarm sender** posts new alarms to a Slack channel.

So the path of an alarm configuration change is: CSV edited in a pull request, XML generated
by the workflow, merged to `main`, picked up by the sidecar, reloaded by the alarm server.

## Deploying

The repository has two kustomize directories, each applied on its own. Always look at the
diff first. When the cluster matches the repository, the diff is empty.

The Strimzi operator:

```sh
kubectl diff -k operator
kubectl apply -k operator
```

Everything else:

```sh
kubectl diff -k base
kubectl apply -k base
```

The operator is kept separate because an operator upgrade has to finish rolling the Kafka pods
before anything else is changed.

Some things to know when applying `base/`:

- The alarm server StatefulSet always reports `configured`, even when nothing changed. Check
  the age of the pod to see whether it really restarted.
- Selectors cannot be changed on a Deployment or StatefulSet that already exists. A change
  to one means deleting the object and applying again.
- Kustomize does not delete objects that are removed from the base. Delete those by hand.
- Do not apply the alarm server file directly with `kubectl apply -f`. It refers to configmaps
  by the names kustomize generates.

## Upgrading the Strimzi operator

Download the new release bundle from
[Strimzi releases](https://github.com/strimzi/strimzi-kafka-operator/releases), replace
`namespace: myproject` with `namespace: nalms-dev`, commit it in `operator/` in place of the
old bundle file, update the file name in `operator/kustomization.yaml`, and apply it. The
operator then rolls the Kafka pods automatically. Check the release notes for the supported
Kafka versions and upgrade path before jumping versions, and update the versions listed in
the top level README.

## Releasing a new sidecar image

The source is in `images/gitsync/`.

```sh
docker build -t tidacs/nalms-config-sync:<X.Y.Z> images/gitsync
docker push tidacs/nalms-config-sync:<X.Y.Z>
```

Then update the image tag in `base/phoebus-alrm-srv-*.yaml` and apply `base/`. Push the image
before applying. Rolling the pod restarts the alarm server.

## Checking that a configuration change was picked up

The sidecar log shows each new commit it synced and that it ran the hook:

```sh
kubectl -n nalms-dev logs phoebus-alrm-srv-cryo-0 -c git-sync --tail=20
```

The file the alarm server is using should be the same size as the one in the checkout, and
there should be no restart waiting to be sent:

```sh
kubectl -n nalms-dev exec phoebus-alrm-srv-cryo-0 -c git-sync -- \
  sh -c 'ls -la /tmp/pv-config/nalms-deployment.git/alarm-config /tmp/nalms; ls /tmp/restart-pending-* 2>/dev/null || echo "no restart pending"'
```

The alarm server log shows the reload and how long it took:

```sh
kubectl -n nalms-dev logs phoebus-alrm-srv-cryo-0 -c phoebus-alrm-srv-cryo --since=15m \
  | grep -E "Restart|Importing|Time to|Total|stabilized|Start handling|timed out"
```

The alarm sender logs every message it decided not to post because it was more than a minute old:

```sh
kubectl -n nalms-dev logs deploy/loki-alrm-send-cryo --since=15m | tail -40
```

## Things that look wrong but are not

- **`base/xml/cryo.xml` is an empty configuration.** It is a placeholder that is copied into the
  pod at start so that the file exists before the sidecar's first sync. The alarm server does
  not load it, because its configuration is named `cryo` in lowercase and the server expects
  `CRYO`. Keep it that way. The real configuration is `alarm-config/cryo.xml`.
- **"connection timed out" in the alarm server log** after a reload means those PVs did not
  connect within 30 seconds, which is normal when the IOCs behind them are down.
- **PVs that were disconnected stay in the UNDEFINED state** after they reconnect, until the
  alarm is acknowledged. While a PV is latched like this, the Slack channel does not get new
  alarms for it. After a long outage, acknowledge these in Phoebus.
- **The LCLS alarm server and logger are commented out** in `base/kustomization.yaml`. They are
  not deployed.

## Adding another alarm configuration

Using LCLS as the example:

1. Make sure `alarm-config/lcls.csv` passes the checks described in
   [Editing alarm configurations](editing-alarms.md).
2. Add `lcls` to `CONFIGS` in `.github/workflows/convert_csv_to_xml.yml`, so the XML is
   generated and committed for it.
3. Uncomment `phoebus-alrm-srv-lcls.yaml` in `base/kustomization.yaml`, and the logger if it
   is wanted.
4. Check the diff and apply `base/`.
