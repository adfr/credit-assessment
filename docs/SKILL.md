---
name: cloudera
description: Automate Cloudera Data Platform (CDP) deployments using Ansible. Use when working with CDP Public Cloud, Private Cloud, Cloudera Manager, Data Services (CDF, CDE, CDW, CML, OpDB), or when generating Ansible playbooks for Cloudera infrastructure. Triggers include mentions of Cloudera, CDP, Data Hub, Data Lake, Cloudera Manager, or Cloudera Ansible collections.
---

# Cloudera Automation Skill

Automate Cloudera Data Platform deployments using the official Cloudera Labs Ansible collections.

## Architecture Overview

Cloudera Labs provides four main Ansible collections:

| Collection | Purpose | Use Case |
|------------|---------|----------|
| `cloudera.cloud` | CDP Public Cloud APIs | Environments, Datalakes, Data Services |
| `cloudera.cluster` | Cloudera Manager APIs | On-premise clusters, DataHubs, services |
| `cloudera.exe` | Deployment utilities | Host prep, databases, TLS, Kerberos |
| `cloudera.services` | Runtime services (internal) | Service configuration |

## Collection Selection Guide

**Use `cloudera.cloud` when:**
- Managing CDP Public Cloud environments
- Creating/managing Datalakes, DataHubs
- Working with Data Services (CDF, CDE, CDW, CML, OpDB)
- Managing CDP IAM users/groups

**Use `cloudera.cluster` when:**
- Interacting with Cloudera Manager directly
- Managing on-premise Private Cloud clusters
- Configuring cluster services (HDFS, Hive, Impala, etc.)
- Managing parcels, hosts, roles

**Use `cloudera.exe` when:**
- Preparing hosts (OS, kernel, prerequisites)
- Setting up databases (PostgreSQL)
- Configuring TLS/Kerberos
- Installing CM agents/server

## Authentication

### CDP Public Cloud
```yaml
# Uses CDP CLI credentials (~/.cdp/credentials)
# Or environment variables:
# CDP_ACCESS_KEY_ID, CDP_PRIVATE_KEY
```

### Cloudera Manager
```yaml
cloudera.cluster.service:
  host: "cm.example.com"
  port: 7183
  username: admin
  password: "{{ cm_password }}"
  # For TLS:
  verify_tls: true
  ca_path: /path/to/ca.pem
```

## Common Patterns

### List CDP Environments
```yaml
- cloudera.cloud.env_info:
  register: environments
```

### Create DataHub Cluster
```yaml
- cloudera.cloud.datahub_cluster:
    name: my-datahub
    environment: my-env
    definition: "7.2.18 - Data Engineering: Apache Spark, Apache Hive"
    state: present
```

### Manage Cloudera Manager Service
```yaml
- cloudera.cluster.service:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    cluster: my-cluster
    name: hdfs
    type: HDFS
    state: started
```

### Host Prerequisites
```yaml
- import_role:
    name: cloudera.exe.prereq_os
- import_role:
    name: cloudera.exe.prereq_jdk
- import_role:
    name: cloudera.exe.prereq_database
```

## Module Quick Reference

### cloudera.cloud modules
- `env` / `env_info` - Environments
- `datalake` / `datalake_info` - Datalakes
- `datahub_cluster` / `datahub_cluster_info` - DataHubs
- `de` / `de_info` - Data Engineering
- `df_service` / `df_deployment` - DataFlow
- `dw_cluster` / `dw_virtual_warehouse` - Data Warehouse
- `ml` / `ml_info` - Machine Learning
- `opdb` / `opdb_info` - Operational Database
- `iam_group` / `iam_user_info` - IAM

### cloudera.cluster modules
- `cluster` / `cluster_info` - Cluster lifecycle
- `service` / `service_info` - Service management
- `parcel` / `parcel_info` - Parcel management
- `host` / `host_info` - Host management
- `cm_config` - Cloudera Manager configuration
- `cm_kerberos` - Kerberos setup
- `cm_autotls` - Auto-TLS configuration

### cloudera.exe roles
- `prereq_*` - Host prerequisites (os, jdk, kernel, etc.)
- `postgresql_server` - Database setup
- `cm_server` / `cm_agent` - CM installation
- `tls_*` - TLS certificate management
- `freeipa_*` - FreeIPA/Kerberos setup

## Execution Environment

Use `cldr-runner` container images for consistent execution:
```yaml
# ansible-navigator.yml
ansible-navigator:
  execution-environment:
    image: ghcr.io/cloudera-labs/cldr-runner-aws:latest
```

Available tags: `base`, `aws`, `azure`, `gcp`, `full`

## API Documentation

- cloudera.cloud: https://cloudera-labs.github.io/cloudera.cloud/
- cloudera.cluster: https://cloudera-labs.github.io/cloudera.cluster/
- cloudera.exe: https://cloudera-labs.github.io/cloudera.exe/

## References

For detailed module parameters and examples:
- See [cloud-modules.md](cloud-modules.md) for CDP Public Cloud
- See [cluster-modules.md](cluster-modules.md) for Cloudera Manager
- See [exe-roles.md](exe-roles.md) for deployment utilities
