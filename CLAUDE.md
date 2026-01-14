# Cloudera Automation Project

This project automates Cloudera Data Platform (CDP) deployments using the official Cloudera Labs Ansible collections.

## Skill Documentation

Reference the detailed documentation in `/docs/cloudera/` when working with:
- CDP Public Cloud environments and data services
- Cloudera Manager clusters and services
- Host preparation and infrastructure setup

## Quick Reference

### Collection Selection

| Need | Collection | Example |
|------|------------|---------|
| CDP Public Cloud | `cloudera.cloud` | Environments, Datalakes, CML, CDE, CDW |
| Cloudera Manager | `cloudera.cluster` | On-prem clusters, services, parcels |
| Host Setup | `cloudera.exe` | OS prep, databases, TLS, CM install |

### Common Tasks

**List CDP environments:**
```yaml
- cloudera.cloud.env_info:
  register: environments
```

**Create a DataHub:**
```yaml
- cloudera.cloud.datahub_cluster:
    name: my-datahub
    environment: my-env
    definition: "7.2.18 - Data Engineering: Apache Spark, Apache Hive"
```

**Manage CM service:**
```yaml
- cloudera.cluster.service:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    cluster: my-cluster
    name: hdfs
    state: started
```

**Prepare hosts:**
```yaml
- import_role:
    name: cloudera.exe.prereq_os
- import_role:
    name: cloudera.exe.prereq_jdk
```

## Authentication

### CDP Public Cloud
Uses `~/.cdp/credentials` or environment variables:
- `CDP_ACCESS_KEY_ID`
- `CDP_PRIVATE_KEY`

### Cloudera Manager
```yaml
host: cm.example.com
port: 7183
username: admin
password: "{{ cm_password }}"
```

## Documentation

- `/docs/cloudera/SKILL.md` - Architecture overview
- `/docs/cloudera/cloud-modules.md` - CDP Public Cloud modules
- `/docs/cloudera/cluster-modules.md` - Cloudera Manager modules
- `/docs/cloudera/exe-roles.md` - Deployment utility roles

## External References

- [cloudera.cloud docs](https://cloudera-labs.github.io/cloudera.cloud/)
- [cloudera.cluster docs](https://cloudera-labs.github.io/cloudera.cluster/)
- [cloudera.exe docs](https://cloudera-labs.github.io/cloudera.exe/)
