# cloudera.exe Roles Reference

Opinionated deployment utilities for Cloudera infrastructure.

## Installation
```bash
ansible-galaxy collection install cloudera.exe
```

## Host Preparation Roles

### prereq_os
General OS configuration.
```yaml
- hosts: cluster
  roles:
    - role: cloudera.exe.prereq_os
      vars:
        # Disable IPv6
        disable_ipv6: true
        # Update packages
        update_packages: true
```

### prereq_kernel
Kernel parameter tuning.
```yaml
- import_role:
    name: cloudera.exe.prereq_kernel
  vars:
    # Override specific settings
    vm_swappiness: 1
```

### prereq_jdk
Install JDK.
```yaml
- import_role:
    name: cloudera.exe.prereq_jdk
  vars:
    java_version: 11
    # Or specify package
    # jdk_package: java-11-openjdk-devel
```

### prereq_thp
Disable Transparent Huge Pages.
```yaml
- import_role:
    name: cloudera.exe.prereq_thp
```

### prereq_ntp
Configure NTP/chrony.
```yaml
- import_role:
    name: cloudera.exe.prereq_ntp
  vars:
    ntp_servers:
      - 0.pool.ntp.org
      - 1.pool.ntp.org
```

### prereq_selinux
Manage SELinux.
```yaml
- import_role:
    name: cloudera.exe.prereq_selinux
  vars:
    selinux_state: permissive  # enforcing, permissive, disabled
```

### prereq_firewall
Disable firewall.
```yaml
- import_role:
    name: cloudera.exe.prereq_firewall
```

### prereq_rngd
Random number generator for entropy.
```yaml
- import_role:
    name: cloudera.exe.prereq_rngd
```

### prereq_network_dns
DNS and hostname configuration.
```yaml
- import_role:
    name: cloudera.exe.prereq_network_dns
  vars:
    set_hostname: true
    dns_servers:
      - 10.0.0.2
```

## Database Roles

### postgresql_server
Install and configure PostgreSQL.
```yaml
- hosts: db_server
  roles:
    - role: cloudera.exe.postgresql_server
      vars:
        postgresql_version: 14
        postgresql_listen_addresses: "*"
        postgresql_max_connections: 500
        # HBA rules
        postgresql_hba_entries:
          - type: host
            database: all
            user: all
            address: 10.0.0.0/8
            method: md5
```

### prereq_database
Create databases for services.
```yaml
- import_role:
    name: cloudera.exe.prereq_database
  vars:
    database_type: postgresql
    database_host: db.example.com
    databases:
      - name: scm
        user: scm
        password: "{{ scm_db_password }}"
      - name: hive
        user: hive
        password: "{{ hive_db_password }}"
```

### Service-specific database roles
```yaml
# Each creates database + user for specific service
- import_role:
    name: cloudera.exe.prereq_cm_database
- import_role:
    name: cloudera.exe.prereq_hive_database
- import_role:
    name: cloudera.exe.prereq_hue_database
- import_role:
    name: cloudera.exe.prereq_oozie_database
- import_role:
    name: cloudera.exe.prereq_ranger_database
- import_role:
    name: cloudera.exe.prereq_schemaregistry_database
- import_role:
    name: cloudera.exe.prereq_smm_database
```

## Cloudera Manager Roles

### cm_repo
Configure CM repository.
```yaml
- import_role:
    name: cloudera.exe.cm_repo
  vars:
    cloudera_manager_repo_url: "https://archive.cloudera.com/cm7/7.11.3/"
    # For authenticated repos
    cloudera_manager_repo_username: "{{ paywall_user }}"
    cloudera_manager_repo_password: "{{ paywall_pass }}"
```

### cm_server
Install CM server.
```yaml
- hosts: cm_server
  roles:
    - role: cloudera.exe.cm_server
      vars:
        cloudera_manager_database_type: postgresql
        cloudera_manager_database_host: db.example.com
        cloudera_manager_database_name: scm
        cloudera_manager_database_user: scm
        cloudera_manager_database_password: "{{ scm_db_password }}"
```

### cm_agent
Install CM agent.
```yaml
- hosts: cluster
  roles:
    - role: cloudera.exe.cm_agent
      vars:
        cloudera_manager_host: cm.example.com
        cloudera_manager_port: 7182
```

## TLS/Security Roles

### tls_generate_csr
Generate CSRs on hosts.
```yaml
- import_role:
    name: cloudera.exe.tls_generate_csr
  vars:
    tls_key_size: 4096
    tls_cert_dir: /opt/cloudera/security/pki
    tls_common_name: "{{ ansible_fqdn }}"
    tls_san:
      - "{{ ansible_fqdn }}"
      - "{{ ansible_default_ipv4.address }}"
```

### tls_signing
Sign CSRs with CA.
```yaml
- import_role:
    name: cloudera.exe.tls_signing
  vars:
    tls_ca_cert: /path/to/ca.pem
    tls_ca_key: /path/to/ca.key
```

### tls_install_certs
Deploy signed certificates.
```yaml
- import_role:
    name: cloudera.exe.tls_install_certs
  vars:
    tls_cert_dir: /opt/cloudera/security/pki
```

### tls_keystores
Create Java keystores/truststores.
```yaml
- import_role:
    name: cloudera.exe.tls_keystores
  vars:
    tls_keystore_path: /opt/cloudera/security/jks/keystore.jks
    tls_keystore_password: "{{ keystore_password }}"
    tls_truststore_path: /opt/cloudera/security/jks/truststore.jks
```

## FreeIPA Roles

### freeipa_server
Install FreeIPA server.
```yaml
- hosts: ipa_server
  roles:
    - role: cloudera.exe.freeipa_server
      vars:
        freeipa_realm: EXAMPLE.COM
        freeipa_domain: example.com
        freeipa_admin_password: "{{ ipa_admin_password }}"
        freeipa_ds_password: "{{ ipa_ds_password }}"
```

### freeipa_client
Enroll hosts in FreeIPA.
```yaml
- hosts: cluster
  roles:
    - role: cloudera.exe.freeipa_client
      vars:
        freeipa_server: ipa.example.com
        freeipa_domain: example.com
        freeipa_realm: EXAMPLE.COM
        freeipa_admin_principal: admin
        freeipa_admin_password: "{{ ipa_admin_password }}"
```

## Kerberos Roles

### prereq_kerberos
Configure Kerberos clients.
```yaml
- import_role:
    name: cloudera.exe.prereq_kerberos
  vars:
    kerberos_realm: EXAMPLE.COM
    kerberos_kdc_servers:
      - kdc1.example.com
      - kdc2.example.com
    kerberos_admin_server: kdc1.example.com
```

## Service User Roles
Create local users/groups for services.
```yaml
# General pattern - each creates required users
- import_role:
    name: cloudera.exe.prereq_hadoop
- import_role:
    name: cloudera.exe.prereq_hdfs
- import_role:
    name: cloudera.exe.prereq_yarn
- import_role:
    name: cloudera.exe.prereq_hive
- import_role:
    name: cloudera.exe.prereq_impala
- import_role:
    name: cloudera.exe.prereq_hbase
- import_role:
    name: cloudera.exe.prereq_kafka
- import_role:
    name: cloudera.exe.prereq_spark
- import_role:
    name: cloudera.exe.prereq_nifi
- import_role:
    name: cloudera.exe.prereq_ranger
- import_role:
    name: cloudera.exe.prereq_atlas
- import_role:
    name: cloudera.exe.prereq_knox
- import_role:
    name: cloudera.exe.prereq_solr
- import_role:
    name: cloudera.exe.prereq_zookeeper
```

## High-Level Orchestration Roles

### platform
Full platform deployment (orchestrates other roles).
```yaml
- hosts: localhost
  roles:
    - role: cloudera.exe.platform
      vars:
        definition_path: /path/to/definition.yml
```

### infrastructure
Provision cloud infrastructure.
```yaml
- import_role:
    name: cloudera.exe.infrastructure
  vars:
    infra_type: aws  # aws, azure, gcp
    # Provider-specific vars...
```

### runtime
Deploy cluster services.
```yaml
- import_role:
    name: cloudera.exe.runtime
  vars:
    cluster_definition: "{{ definition }}"
```

## Edge/IoT Roles

### efm
Install Edge Flow Manager.
```yaml
- import_role:
    name: cloudera.exe.efm
  vars:
    efm_db_type: postgresql
    efm_db_host: db.example.com
```

### minifi_agent_java
Install MiNiFi Java agent.
```yaml
- import_role:
    name: cloudera.exe.minifi_agent_java
  vars:
    minifi_c2_host: efm.example.com
```

### minifi_agent_cpp
Install MiNiFi C++ agent.
```yaml
- import_role:
    name: cloudera.exe.minifi_agent_cpp
```

## Modules

### cm_prepare_db
Initialize CM database (runs scm_prepare_database.sh).
```yaml
- cloudera.exe.cm_prepare_db:
    database_type: postgresql
    database_host: db.example.com
    database_name: scm
    database_user: scm
    database_password: "{{ scm_db_password }}"
```

### supported
Check support matrix.
```yaml
- cloudera.exe.supported:
    product: CDH
    version: 7.1.9
    os: RHEL
    os_version: "8"
  register: support_check
```

## Common Variables

```yaml
# Repository access
cloudera_manager_repo_url: "https://archive.cloudera.com/cm7/7.11.3/"
cdh_repo_url: "https://archive.cloudera.com/cdh7/7.1.9/parcels/"

# Paywall authentication (if required)
cloudera_manager_repo_username: ""
cloudera_manager_repo_password: ""

# Database defaults
database_type: postgresql
database_host: localhost
database_port: 5432

# Security
tls_enabled: true
kerberos_enabled: true
```
