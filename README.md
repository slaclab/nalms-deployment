# nalms-deployment

Kubernetes deployment for NALMS, the Phoebus-based EPICS alarm system. It runs a Kafka
cluster (managed by the Strimzi operator) that carries the alarm topics, Phoebus alarm
servers for each configured area (LCLS, CRYO), and the alarm logger/sender services.

Currently deployed to the `nalms-dev` namespace on the SLAC k8s cluster with:

- Strimzi operator 1.1.0
- Kafka 4.2.1 (KRaft mode, broker and controller node pools)

## Layout

- `operator/` — the Strimzi operator bundle, applied on its own.
- `base/` — all other active manifests: the Kafka cluster and node pools, Phoebus alarm
  servers, and the alarm logger/sender deployments, tied together with kustomize.
- `alarm-config/` — the alarm configurations. Each has a CSV file, which is the source to
  edit, and a Phoebus XML file generated from it. The XML is generated and committed by
  CI, so it should not be edited by hand.
- `tools/` — the CSV to XML converter, the validation scripts and the XML schema.
- `images/` — source for container images built from this repository, currently the
  git-sync sidecar that delivers alarm configuration changes to the alarm servers.
- `docs/` — MkDocs sources for the documentation site.

## Deploying

The Strimzi operator bundle is applied on its own (it is intentionally not part of the
kustomize base). Check what would change before applying:

```sh
kubectl diff -k operator
kubectl apply -k operator
```

Everything else is applied the same way from `base/`:

```sh
kubectl diff -k base
kubectl apply -k base
```

To upgrade the operator, download the new release bundle from
[Strimzi releases](https://github.com/strimzi/strimzi-kafka-operator/releases), replace
`namespace: myproject` with `namespace: nalms-dev`, commit it in `operator/` in place of the
old bundle file, update the file name in `operator/kustomization.yaml`, and apply it. The operator then rolls the Kafka pods automatically. Check the
release notes for the supported Kafka versions and upgrade path before jumping versions.
