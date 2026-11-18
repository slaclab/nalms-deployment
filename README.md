# nalms-deployment

Kubernetes deployment for NALMS, the Phoebus-based EPICS alarm system, together with the
alarm configurations it runs. It has a Kafka cluster (managed by the Strimzi operator) that
carries the alarm topics, a Phoebus alarm server for each deployed alarm configuration
(currently CRYO), and the alarm logger/sender services.

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
- `docs/` — the guides linked below.

## Guides

- [Editing alarm configurations](docs/editing-alarms.md) — the CSV format, what the pull
  request checks do, and what happens when a change is merged.
- [Operations](docs/operations.md) — how the pieces fit together, deploying, upgrading,
  and checking that a configuration change was picked up.
