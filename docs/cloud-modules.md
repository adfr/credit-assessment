# cloudera.cloud Module Reference

CDP Public Cloud management via Ansible.

## Installation
```bash
ansible-galaxy collection install cloudera.cloud
```

## Environment Modules

### env
Create, update, or delete CDP environments.
```yaml
- cloudera.cloud.env:
    name: my-environment
    state: present
    cloud: aws  # aws, azure, gcp
    region: us-west-2
    credential: my-aws-cred
    public_key_text: "{{ lookup('file', '~/.ssh/id_rsa.pub') }}"
    # Network
    network_cidr: 10.0.0.0/16
    vpc_id: vpc-12345  # existing VPC
    subnet_ids: [subnet-a, subnet-b]
    security_access:
      cidr: 0.0.0.0/0
    # Storage (AWS)
    log_identity: arn:aws:iam::123456:instance-profile/log-role
    log_location: s3://my-bucket/logs
    data_access_role: arn:aws:iam::123456:role/data-role
```

### env_info
```yaml
- cloudera.cloud.env_info:
    name: my-environment  # optional, omit for all
  register: env_result
```

### env_cred
Manage CDP credentials.
```yaml
- cloudera.cloud.env_cred:
    name: my-aws-cred
    cloud: aws
    role_arn: arn:aws:iam::123456:role/cdp-cross-account
    state: present
```

## Datalake Modules

### datalake
```yaml
- cloudera.cloud.datalake:
    name: my-datalake
    environment: my-environment
    state: present
    # Optional
    scale: LIGHT_DUTY  # LIGHT_DUTY, MEDIUM_DUTY_HA
    runtime: 7.2.18
    recipes:
      - name: my-recipe
        instance_group: master
```

### datalake_info
```yaml
- cloudera.cloud.datalake_info:
    name: my-datalake
  register: dl_info
```

### datalake_backup
```yaml
- cloudera.cloud.datalake_backup:
    datalake: my-datalake
    backup_name: weekly-backup
    backup_location: s3://backup-bucket/datalake
```

## DataHub Modules

### datahub_cluster
```yaml
- cloudera.cloud.datahub_cluster:
    name: my-datahub
    environment: my-environment
    state: present
    # Use definition name or template
    definition: "7.2.18 - Data Engineering: Apache Spark, Apache Hive"
    # Or custom template
    # template: my-custom-template
    # instance_groups:
    #   - name: master
    #     type: MASTER
    #     count: 1
    #     instance_type: m5.2xlarge
```

### datahub_cluster_info
```yaml
- cloudera.cloud.datahub_cluster_info:
    name: my-datahub
    environment: my-environment
  register: dh_info
```

### datahub_definition_info
List available cluster definitions.
```yaml
- cloudera.cloud.datahub_definition_info:
  register: definitions
```

### datahub_template_info
```yaml
- cloudera.cloud.datahub_template_info:
  register: templates
```

## Data Engineering (CDE)

### de
Enable/disable Data Engineering service.
```yaml
- cloudera.cloud.de:
    name: my-de-service
    environment: my-environment
    state: present
    instance_type: m5.2xlarge
    min_instances: 0
    max_instances: 10
    enable_public_endpoint: true
```

### de_virtual_cluster
```yaml
- cloudera.cloud.de_virtual_cluster:
    name: my-vc
    service: my-de-service
    state: present
    cpu_requests: 4
    memory_requests: 8Gi
    spark_version: SPARK3
```

## DataFlow (CDF)

### df_service
```yaml
- cloudera.cloud.df_service:
    name: my-df-service
    environment: my-environment
    state: present
```

### df_deployment
```yaml
- cloudera.cloud.df_deployment:
    name: my-flow-deployment
    service: my-df-service
    flow_name: my-flow
    flow_version: 1
    state: present
    nifi_version: 1.18.0.2.3.9.0-3
    auto_scaling:
      enabled: true
      min_nodes: 1
      max_nodes: 3
```

### df_customflow
```yaml
- cloudera.cloud.df_customflow:
    name: my-custom-flow
    file: /path/to/flow.json
    state: present
```

## Data Warehouse (CDW)

### dw_cluster
```yaml
- cloudera.cloud.dw_cluster:
    environment: my-environment
    state: present
```

### dw_database_catalog
```yaml
- cloudera.cloud.dw_database_catalog:
    cluster_id: "{{ dw_cluster.id }}"
    name: my-catalog
    state: present
```

### dw_virtual_warehouse
```yaml
- cloudera.cloud.dw_virtual_warehouse:
    cluster_id: "{{ dw_cluster.id }}"
    catalog_id: "{{ catalog.id }}"
    name: my-hive-vw
    type: hive  # hive, impala
    size: xsmall
    state: present
```

## Machine Learning (CML)

### ml
```yaml
- cloudera.cloud.ml:
    name: my-ml-workspace
    environment: my-environment
    state: present
    # Optional
    enable_governance: true
    enable_model_metrics: true
    public_loadbalancer: true
```

### ml_workspace_access
```yaml
- cloudera.cloud.ml_workspace_access:
    workspace: my-ml-workspace
    environment: my-environment
    user: user@example.com
    state: present
```

## Operational Database (OpDB)

### opdb
```yaml
- cloudera.cloud.opdb:
    name: my-opdb
    environment: my-environment
    state: present
    # Optional
    scale_type: LIGHT
    storage_type: CLOUD_WITH_EPHEMERAL
```

## IAM Modules

### iam_group
```yaml
- cloudera.cloud.iam_group:
    name: my-group
    state: present
    users:
      - user1@example.com
      - user2@example.com
    roles:
      - EnvironmentAdmin
    resource_roles:
      - resource: my-environment
        role: DEAdmin
```

### iam_user_info
```yaml
- cloudera.cloud.iam_user_info:
  register: users
```

## Lookup Plugins

### datalake_runtime
```yaml
- set_fact:
    runtime: "{{ lookup('cloudera.cloud.datalake_runtime', 'default') }}"
```

### datahub_definition
```yaml
- set_fact:
    definition: "{{ lookup('cloudera.cloud.datahub_definition', 
                          environment='my-env',
                          cloud='aws',
                          product='Data Engineering') }}"
```

## Common Variables

```yaml
# CDP authentication (usually via environment or ~/.cdp/credentials)
cdp_profile: default

# Common parameters across modules
cdp_endpoint_url: https://api.us-west-1.cdp.cloudera.com
```
