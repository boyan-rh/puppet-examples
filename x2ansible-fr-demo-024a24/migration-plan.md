# MIGRATION FROM PUPPET TO ANSIBLE

This is a Puppet control repository containing five independently versioned local Puppet modules, a role/profile composition layer, Hiera data, and development/test scaffolding. The target estate spans Debian/Ubuntu and Red Hat-family hosts, with Ubuntu 24.04 and Rocky Linux 9 explicitly represented. The main workload is a Python API backed by PostgreSQL, fronted by HAProxy, plus a Redis deployment. Migration complexity is moderate: most resources map cleanly to Ansible packages, templates, services, users, repositories, and firewall rules, but Hiera precedence, PuppetDB-based Redis discovery, encrypted Hiera values, and application/database cutover coordination require deliberate design.

Plan for approximately 6–10 weeks for discovery confirmation, role implementation, automated tests, parallel validation, pilot, and production rollout for a small platform team. This estimate assumes existing host access, a chosen Ansible Controller/inventory source, and ownership of the application, database, and load-balancer services. Retain the user-mandated PostgreSQL **19** target throughout design and testing; the current Puppet data specifies PostgreSQL 16 and must not be replicated unchanged.

## Module Migration Plan

This repository contains Puppet modules that need individual migration planning:

### MODULE INVENTORY

- **base_utils**:
  - Description: Common operating-system utility baseline that manages `/etc/motd` from an ERB template and installs a Hiera-defined package list. It also contains custom facts, functions/types, Bolt plans/tasks, and helper manifests that should be evaluated as supporting automation rather than translated mechanically.
  - Path: `site-modules/base_utils`
  - Technology: Puppet
  - Key Features: OS-specific Hiera data for Debian and RedHat, custom Facter fact, MOTD management, typed helper interfaces, health-check and rolling-restart Bolt assets.

- **profile_app_stack**:
  - Description: Orchestrates a Python application stack in a strict Python → database → application → systemd service → monitoring sequence. Configuration is Hiera-driven and includes Git deployment inputs, Gunicorn/Uvicorn settings, PostgreSQL connection configuration, logging, backup and health-check scripts.
  - Path: `site-modules/profile_app_stack`
  - Technology: Puppet
  - Key Features: Python application parameters, Git source/revision, PostgreSQL URL built by a custom Puppet Ruby function, systemd service templating, log rotation, monitoring/health-check artifacts.

- **profile_haproxy**:
  - Description: HAProxy load-balancer profile that installs, configures, services, and firewall-enables HAProxy, with optional backend discovery. It renders multi-backend configuration from deeply merged Hiera data and includes static HTTP error pages.
  - Path: `site-modules/profile_haproxy`
  - Technology: Puppet
  - Key Features: HAProxy service/configuration lifecycle, static web and API backend pools with health checks and weights, stats endpoint, TLS parameters, firewall management, optional discovery path, Debian/RedHat and node/datacenter/cluster data.

- **profile_postgresql**:
  - Description: PostgreSQL package installation profile that configures the PostgreSQL Global Development Group (PGDG) APT repository, installs version-specific server and contrib packages plus `libpq-dev`, and manages the PostgreSQL service.
  - Path: `site-modules/profile_postgresql`
  - Technology: Puppet
  - Key Features: PGDG APT repository/key configuration, version-derived package names, PostgreSQL service management. Source Hiera currently sets version 16; the Ansible target must instead install and validate PostgreSQL **19**.

- **profile_redis_cluster**:
  - Description: Redis deployment profile that delegates server management to the external `puppet-redis` module and queries PuppetDB for nodes assigned the Redis profile.
  - Path: `site-modules/profile_redis_cluster`
  - Technology: Puppet
  - Key Features: Redis service/package configuration, network bind on all interfaces, password authentication, 2 GiB maximum memory with `allkeys-lru`, AOF persistence, PuppetDB-driven cluster-node discovery.

The following Puppet composition directories are not standalone modules with a `manifests/init.pp` entrypoint, but must be migrated as Ansible playbook/role composition:

- `site-modules/profile/manifests/`: legacy or alternate profile classes for base, application stack, Redis, and HAProxy; assess for overlap against the versioned `profile_*` modules before implementation.
- `site-modules/role/manifests/`: role classes (`app_server`, `app_stack`, `haproxy`, `redis_cluster`) that should become top-level playbooks or inventory-driven role assignments.
- `site-modules/puppetdb_query_stub/`: a custom Puppet function stub used by the Redis profile; replace rather than preserve this Puppet-specific interface.

### Infrastructure Files

- `Puppetfile`: Root Forge dependency lock-style declaration. It pins stdlib 9.7.0, concat 9.0.2, firewall 8.1.3, vcsrepo 6.1.0, redis 11.0.0, systemd 7.1.0, inifile 6.1.1, and apt 9.4.0. Replace Puppet Forge installation with Ansible collections/roles pinned in `collections/requirements.yml` and, where necessary, role requirements.
- `environment.conf`: Defines Puppet module paths (`site-modules:modules:$basemodulepath`). Ansible must explicitly establish the equivalent repository layout: `roles/`, `playbooks/`, `inventories/`, `group_vars/`, `host_vars/`, and `collections/`.
- `hiera.yaml`: Root Hiera 5 hierarchy applies node, OS family, environment, then common data. Recreate precedence intentionally with Ansible inventory, `host_vars`, `group_vars`, environment inventories, and defaults; test resulting effective variables.
- `data/common.yaml` and `data/environment/{production,staging}.yaml`: Root-level environment configuration inputs. Classify each variable into environment/group/host scope when creating Ansible inventory.
- `manifests/site.pp`: Puppet site classification. It creates a local test Git repository/application and includes `role::app_server`; it also orders the test repository before the application class. Translate its test fixture separately from production deployment, and retain only intentional global Git configuration behavior.
- `site-modules/*/metadata.json`: Module-specific compatibility and Puppet dependency declarations. They establish Puppet 7–8 support and OS support; they are source metadata, not target runtime dependencies.
- `site-modules/*/hiera.yaml` and `site-modules/*/data/`: Module-local data hierarchies. HAProxy notably has node, OS, environment, datacenter, and cluster scopes; preserve this scope model in Ansible variables/inventory.
- `site-modules/profile_haproxy/Puppetfile` and `site-modules/profile_redis_cluster/Puppetfile`: Local dependency declarations that partially overlap root pins. Consolidate the chosen Ansible dependency versions centrally.
- `Vagrantfile` and `vagrant-provision.sh`: Ubuntu 24.04 Vagrant development environment using libvirt, a private network, and forwarded HTTP/HTTPS ports. Convert provisioning to an Ansible Vagrant provisioner or use it as an integration-test target.
- `test/Containerfile` and `test/run.sh`: Rocky Linux 9/Puppet 8 container test setup that installs Forge modules through r10k. Replace with an Ansible execution-environment or Molecule/integration-test image; do not carry Puppet agent/r10k installation into the target image.
- `x2a-rules/d5872732-f37d-4221-8ddd-af1d68455083.md`: Migration-rule/support documentation that should be reviewed by the migration team before implementation, without treating it as executable infrastructure.

### Target Details

- **Operating System**: Explicit support is Red Hat Enterprise Linux-compatible 8/9, Debian 11/12, Ubuntu 22.04/24.04; Ubuntu 24.04 is the Vagrant box and Rocky Linux 9 is the container test base. PostgreSQL profile data explicitly targets Debian 12 and Ubuntu 24.04 via APT/PGDG. Create and test package/service variable maps per OS family rather than assuming package names are portable.
- **Virtual Machine Technology**: Vagrant with the libvirt provider is explicitly configured for the development VM. Production virtualization is not specified.
- **Cloud Platform**: Not specified. No cloud provider tooling or metadata endpoint usage was identified.

## Migration Approach

Implement an Ansible repository with collection and role dependency locks, separate inventories for staging/production, and roles such as `base_utils`, `postgresql`, `redis`, `app_stack`, and `haproxy`. Use top-level playbooks corresponding to the Puppet roles. Establish an agreed variable contract before porting templates: classify Hiera data by common, OS, environment, datacenter/cluster, and host scope, then write automated assertions for effective configuration on representative nodes.

Run Puppet and Ansible in parallel only where safe. Use check mode, staged canaries, service-specific smoke tests, HAProxy configuration validation, application health checks, and PostgreSQL backup/restore tests before removing Puppet enforcement. Assign clear owners: platform engineering for framework/inventory/secrets, database engineering for PostgreSQL 19, application engineering for app/migrations, and network/security for HAProxy/firewall/TLS validation.

### Key Dependencies to Address

- **puppetlabs-stdlib (9.7.0 / module constraints)**: Replace generic Puppet resource helpers and lookups with native Ansible modules, role defaults, argument validation, and explicit `assert` tasks.
- **puppetlabs-vcsrepo (6.1.0)**: Replace application Git checkout behavior with `ansible.builtin.git`, deploy keys/tokens sourced from Ansible Vault or an external secret manager, and a pinned revision policy.
- **puppetlabs-apt (9.4.0)**: Replace with `ansible.builtin.deb822_repository` or `apt_repository`, repository key management, and `apt`; use the current, supported PGDG installation method for PostgreSQL 19.
- **puppetlabs-concat (9.0.2)**: Replace configuration fragment assembly with deterministic Jinja2 templates or `assemble` only where fragment ownership is truly required.
- **puppetlabs-firewall (8.1.3)**: Replace with `ansible.posix.firewalld`, `community.general.ufw`, or native nftables tasks selected by OS and organizational firewall standard. Restrict HAProxy listener/stats access explicitly.
- **puppet-redis (11.0.0) and puppet-systemd/inifile transitive dependencies**: Use maintained Ansible package/template/service tasks or a reviewed collection role. Preserve required Redis directives, but validate the actual Redis version and OS package capabilities.
- **PuppetDB query function**: Replace PuppetDB node discovery with Ansible dynamic inventory, inventory groups, CMDB-backed inventory, or a centrally maintained `redis_cluster` group. The existing profile queries class assignments but does not show a complete cluster-formation implementation; confirm the intended topology before migration.
- **Puppet custom Ruby/Facter functions and Bolt tasks**: Rewrite the database URL calculation in Jinja2/role variables and map facts to `ansible_facts`. Convert service health checks and rolling restart plans to playbooks with `uri`, `service`, `serial`, handlers, and failure thresholds.

### Security Considerations

- **Encrypted Hiera credentials**: `profile_app_stack` contains a `db_password` marked `ENC[PKCS7,...]`; `profile_haproxy` contains an encrypted stats password in the same form. Confirm the PKCS7 decryption workflow and migrate plaintext values only through Ansible Vault or an approved external secret manager. Do not copy ciphertext into templates or logs.
- **Default/placeholder secrets**: `profile_app_stack` defaults `secret_key` to `changeme`; `profile_redis_cluster` defaults the Redis password to `CHANGEME`. Treat both as deployment blockers: require non-default secrets through validation and rotate them during cutover.
- **Redis exposure**: Redis is configured with `bind => '0.0.0.0'` and password authentication. Limit inbound port 6379 to approved application/cluster networks using host firewall and network controls; consider TLS and protected-mode requirements appropriate to the selected Redis version.
- **HAProxy administrative and TLS assets**: The stats endpoint is enabled on port 9000 with an administrator user/password. Restrict it to management networks, use strong secret storage, and verify TLS certificate/key ownership and permissions (`/etc/ssl/private` must not be broadly readable). Preserve at least TLS 1.2 and review cipher policy against current organizational standards.
- **PostgreSQL repository trust**: PGDG is configured using a downloaded signing key URL and key ID. Use a verified repository/key workflow, pin expected source/release, and ensure PostgreSQL 19 packages come from a supported repository for each target OS.
- **Application deployment credentials and runtime configuration**: The Git URL is public in reviewed data, but deployment may later need private repository credentials. Store SCM credentials, database credentials, application secret keys, and any TLS materials outside Git. Mark secret-bearing Ansible tasks `no_log: true`.
- **File/service privileges**: Retain least privilege for application user/group, systemd unit, environment file, log directories, scripts, and database assets. Explicitly set owner/group/mode rather than relying on defaults.
- **Test fixture behavior**: `site.pp` sets `/etc/gitconfig` `safe.directory = *`, which weakens Git safe-directory protections. Do not migrate this globally without a documented, constrained operational need.

### Technical Challenges

- **PostgreSQL 16-to-19 change requirement**: The source Hiera value is 16, while the required target is 19. This is an intentional version migration, not a like-for-like configuration conversion. Confirm package availability for Debian/Ubuntu targets, repository support, data-directory and service naming differences, extension compatibility, client library compatibility, backup/restore or `pg_upgrade` strategy, rollback point, and application/Alembic migration sequence. Have the DBA own a rehearsed non-production upgrade before cutover.
- **Hiera hierarchy translation**: Root and module-local Hiera files express precedence across node, OS, environment, datacenter, cluster, and common data. Ansible variable precedence can accidentally override intended settings. Define a documented inventory model and avoid competing definitions of the same variables across role defaults, group vars, and host vars.
- **PuppetDB-based discovery**: Redis depends on a live PuppetDB query for nodes classified with its class. Ansible has no equivalent implicit runtime catalog query. Make membership explicit in inventory or integrate approved dynamic inventory/CMDB data, then test node addition/removal and rolling operations.
- **Configuration ordering and handlers**: Puppet declares a strict application dependency chain and notification semantics. Implement idempotent Ansible role dependencies plus handlers carefully so app code/config changes restart services only after prerequisites are available; avoid restart storms.
- **Mixed operating systems**: HAProxy, base utilities, application, and Redis support both Debian/Ubuntu and RedHat-family systems, while PostgreSQL source implementation is APT-based. Use OS-specific variable files and CI matrix tests; do not assume repository, firewall, package, service, or filesystem conventions are identical.
- **HAProxy generated configuration**: Deeply merged backend definitions, optional discovery, backend health checks, and static error pages require deterministic Jinja rendering. Validate with `haproxy -c -f` before reload and execute HTTP health checks against each configured pool.
- **Legacy/overlapping composition**: The generic `profile` and `role` trees coexist with named profile modules. Inventory/classification intent is not fully visible in reviewed entrypoints. Resolve which path is authoritative before implementing duplicate roles.

### Migration Order

1. **Foundation and inventory baseline**: Build the Ansible repository structure, dependency pinning, secret integration, inventory hierarchy, CI, and common/base utilities role. Translate non-production test environment provisioning first to provide repeatable Ubuntu 24.04 and Rocky Linux 9 validation targets.
2. **PostgreSQL 19 role and database migration runbook**: Implement the PGDG repository, PostgreSQL **19** packages, service, validation, backup/restore, and rollback procedures. Test application client compatibility and database migration behavior before any application cutover.
3. **Application stack role**: Port Python/runtime prerequisites, Git deployment, database URL/environment rendering, systemd, log rotation, monitoring, backup/health-check scripts, and ordered handlers. Inject all credentials through the selected secret mechanism.
4. **HAProxy role**: Port package/service, templates, backend inventory mapping, firewalling, TLS, error pages, and controlled stats access. Validate configuration and route canary traffic to the migrated application.
5. **Redis role and cluster orchestration**: Replace PuppetDB discovery with explicit/dynamic inventory and deploy Redis with hardened networking and non-placeholder secrets. Perform rolling rollout and functional resilience tests after the topology is confirmed.
6. **Role/playbook composition and Puppet retirement**: Map Puppet `role::*` classifications to Ansible plays/groups, reconcile any legacy `profile` overlap, complete acceptance evidence, disable Puppet enforcement per service wave, and archive Puppet-specific tooling after the agreed observation period.

### Assumptions

- The repository is a Puppet control repository using Puppet 7–8-era modules; no Chef, Salt, or PowerShell modules were identified in the provided tree.
- Only directories with their own `manifests/init.pp` are treated as standalone Puppet modules in the inventory: `base_utils`, `profile_app_stack`, `profile_haproxy`, `profile_postgresql`, and `profile_redis_cluster`.
- The `profile` and `role` directories are composition/legacy classes rather than independently versioned module entrypoints; their exact usage requires confirmation from node classification and production inventories.
- Hiera-encrypted `ENC[PKCS7,...]` values are assumed to be secret material, but their decryption keys, certificate chain, rotation policy, and all other secret locations were not provided.
- The reviewed configuration does not establish whether PostgreSQL is local-only or remote, whether data already exists, whether replication/high availability is required, or which extensions are installed. These items materially affect the PostgreSQL 19 migration plan.
- The PostgreSQL version requirement from the requester supersedes the source `profile_postgresql::version: '16'`; all target design and acceptance criteria must use PostgreSQL 19.
- The Redis profile is called a cluster profile, but the reviewed entrypoint/install code shows discovery and a single Redis server configuration, not explicit cluster-mode, replication, Sentinel, or slot-management directives. Topology and availability requirements must be confirmed.
- HAProxy certificate/key files are referenced by paths, but certificate issuance, distribution, renewal, and whether TLS is enabled in production are not shown.
- Vagrant/libvirt is confirmed only as a development/test virtualization setup; production VM/cloud platform and the Ansible control-plane location are not specified.
- Application repository availability, branch protection/release pinning, Python version compatibility, database schema ownership, monitoring implementation, and backup retention/restore requirements must be confirmed with their respective owners.
- The test container demonstrates Rocky Linux 9 and Puppet 8 module installation but is not proof that every module is currently tested or production-supported on that platform.
