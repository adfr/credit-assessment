# cloudera.cluster Module Reference

Cloudera Manager API automation for on-premise and DataHub clusters.

## Installation
```bash
ansible-galaxy collection install cloudera.cluster
```

## Connection Parameters
All modules require CM connection:
```yaml
cloudera.cluster.<module>:
  host: cm.example.com
  port: 7183  # 7180 for HTTP
  username: admin
  password: "{{ cm_password }}"
  verify_tls: true  # default true
  ca_path: /path/to/ca.pem  # optional
```

## Cluster Modules

### cluster
Manage cluster lifecycle.
```yaml
- cloudera.cluster.cluster:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    name: my-cluster
    state: present  # present, absent, started, stopped, restarted
    display_name: "My Production Cluster"
    cluster_type: BASE_CLUSTER  # BASE_CLUSTER, COMPUTE_CLUSTER
    cdh_version: "7.1.9"
```

### cluster_info
```yaml
- cloudera.cluster.cluster_info:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    name: my-cluster  # optional
  register: clusters
```

## Service Modules

### service
Manage cluster services.
```yaml
- cloudera.cluster.service:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    cluster: my-cluster
    name: hdfs
    type: HDFS
    state: present  # present, absent, started, stopped, restarted
    config:
      dfs_replication: 3
      dfs_encrypt_data_transfer_algorithm: AES/CTR/NoPadding
    role_config_groups:
      - type: DATANODE
        config:
          dfs_data_dir_list: "/dfs/dn"
      - type: NAMENODE
        config:
          dfs_name_dir_list: "/dfs/nn"
```

### service_info
```yaml
- cloudera.cluster.service_info:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    cluster: my-cluster
    name: hdfs  # optional
  register: services
```

### service_config
```yaml
- cloudera.cluster.service_config:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    cluster: my-cluster
    service: hdfs
    parameters:
      dfs_replication: 3
```

## Role Modules

### role
Manage service roles.
```yaml
- cloudera.cluster.role:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    cluster: my-cluster
    service: hdfs
    name: hdfs-DATANODE-1
    type: DATANODE
    host_id: "{{ host_id }}"
    state: present
```

### role_config_group
```yaml
- cloudera.cluster.role_config_group:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    cluster: my-cluster
    service: hdfs
    name: datanode-ssd
    type: DATANODE
    config:
      dfs_data_dir_list: "/ssd/dfs/dn"
```

## Host Modules

### host
Manage CM hosts.
```yaml
- cloudera.cluster.host:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    name: worker01.example.com
    state: present
    # Optional
    rack_id: /default/rack1
```

### host_info
```yaml
- cloudera.cluster.host_info:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
  register: hosts
```

### host_template
Apply role templates to hosts.
```yaml
- cloudera.cluster.host_template:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    cluster: my-cluster
    name: worker-template
    role_config_groups:
      - hdfs/datanode-default
      - yarn/nodemanager-default
```

## Parcel Modules

### parcel
Manage parcels (distribute, activate).
```yaml
- cloudera.cluster.parcel:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    cluster: my-cluster
    product: CDH
    version: 7.1.9-1.cdh7.1.9.p0.44702451
    state: activated  # downloaded, distributed, activated
```

### parcel_info
```yaml
- cloudera.cluster.parcel_info:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    cluster: my-cluster
  register: parcels
```

## Cloudera Manager Configuration

### cm_config
Configure CM server settings.
```yaml
- cloudera.cluster.cm_config:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    parameters:
      PARCEL_DISTRIBUTE_RATE_LIMIT_KBS_PER_SECOND: 51200
      REMOTE_PARCEL_REPO_URLS: "https://archive.cloudera.com/cdh7/7.1.9/parcels/"
```

### cm_config_info
```yaml
- cloudera.cluster.cm_config_info:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
  register: cm_settings
```

### cm_version_info
```yaml
- cloudera.cluster.cm_version_info:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
  register: cm_version
```

## Security Modules

### cm_autotls
Configure Auto-TLS.
```yaml
- cloudera.cluster.cm_autotls:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    state: present
    # Custom CA (optional)
    custom_ca_cert: "{{ lookup('file', 'ca.pem') }}"
    custom_ca_key: "{{ lookup('file', 'ca.key') }}"
```

### cm_kerberos
Configure Kerberos.
```yaml
- cloudera.cluster.cm_kerberos:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    state: present
    kdc_type: MIT KDC
    kdc_host: kdc.example.com
    realm: EXAMPLE.COM
    admin_principal: cloudera-scm/admin@EXAMPLE.COM
    admin_password: "{{ kerberos_admin_pw }}"
```

### cm_license
```yaml
- cloudera.cluster.cm_license:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    license: "{{ lookup('file', 'license.txt') }}"
```

### cm_trial_license
```yaml
- cloudera.cluster.cm_trial_license:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
```

## User Management

### user
```yaml
- cloudera.cluster.user:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    name: newuser
    password: "{{ new_user_password }}"
    roles:
      - ROLE_ADMIN
    state: present
```

## CM Service (Management Service)

### cm_service
Manage the Cloudera Management Service.
```yaml
- cloudera.cluster.cm_service:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    state: started
```

### cm_service_role
```yaml
- cloudera.cluster.cm_service_role:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    name: SERVICEMONITOR
    type: SERVICEMONITOR
    host_id: "{{ cm_host_id }}"
```

## Control Plane (PVC)

### control_plane
Manage Private Cloud Control Plane.
```yaml
- cloudera.cluster.control_plane:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    state: present
    namespace: cdp
```

### data_context
```yaml
- cloudera.cluster.data_context:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    name: my-data-context
    state: present
```

## Generic Resource Modules

### cm_resource
Low-level CM API access.
```yaml
- cloudera.cluster.cm_resource:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    path: /clusters/my-cluster/commands/restart
    method: POST
```

### cm_resource_info
```yaml
- cloudera.cluster.cm_resource_info:
    host: "{{ cm_host }}"
    username: admin
    password: "{{ cm_password }}"
    path: /clusters
  register: api_response
```

## Filter Plugins

### cluster_service_role_hosts
Extract hosts with specific roles.
```yaml
- set_fact:
    datanodes: "{{ cluster_info | cloudera.cluster.cluster_service_role_hosts('hdfs', 'DATANODE') }}"
```

### extract_parcel_urls
```yaml
- set_fact:
    parcel_urls: "{{ manifests | cloudera.cluster.extract_parcel_urls }}"
```

## Lookup Plugins

### cm_service
```yaml
- set_fact:
    hdfs_url: "{{ lookup('cloudera.cluster.cm_service', 
                         host=cm_host, 
                         username='admin',
                         password=cm_password,
                         cluster='my-cluster',
                         service='hdfs') }}"
```
