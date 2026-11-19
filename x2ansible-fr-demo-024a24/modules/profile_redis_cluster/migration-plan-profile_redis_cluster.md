---
source-path: site-modules/profile_redis_cluster
---

# Migration Plan: profile_redis_cluster

**TLDR**: This profile includes the Forge `puppet-redis` module and contains `profile_redis_cluster::install`, which declares the `redis` class. The analyzed dependency manages Redis package installation, directories, configuration, optional systemd units and limits, and service lifecycle through OS-dependent defaults. The profile name does not, from the validated execution structure, establish Redis Cluster protocol configuration, replication, Sentinel, peer discovery, or PuppetDB-driven topology. Redis instance names, effective Hiera values, package names, service names, managed paths, and template render counts must be confirmed from an effective Puppet catalog or representative Puppet-managed host before enforcing Ansible parity.

## Service Type and Instances

**Service Type**: Redis in-memory cache/data store.

**Configured Instances**:
- No exact Redis instance name is confirmed by the supplied structured analysis.
  - `redis::config` may create `redis::instance['default']` when the dependency parameter `default_install` is enabled.
  - Additional named instances may be created from the dependency `$instances` hash through `$instances.each`.
  - The supplied analysis does not establish the value of `default_install` or enumerate `$instances`; therefore, no instance names or instance counts can be treated as authoritative.
  - The profile declares the `redis` class with reported configuration intent for bind address, port, password, memory, and AOF settings, but effective parameter values require catalog or Hiera lookup confirmation.
  - Package name, service name, configuration path, log path, data path, ownership, mode, and service provider are unresolved OS-dependent behavior inherited from `redis::params` and the Forge Redis dependency.

## File Structure

```text
### Manifests
- site-modules/role/manifests/app_server.pp
- site-modules/profile/manifests/cache/redis.pp
- site-modules/profile_redis_cluster/manifests/init.pp
- site-modules/profile_redis_cluster/manifests/install.pp
- site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/init.pp
- site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/preinstall.pp
- site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/install.pp
- site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/config.pp
- site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/instance.pp
- site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/service.pp
- site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/ulimit.pp
- site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/dnfmodule.pp

### Hiera Data
- data/common.yaml
- data/environment/production.yaml
- data/environment/staging.yaml

### Custom Components
- site-modules/profile_redis_cluster/lib/facter/redis_role.rb
```

## Module Explanation

The module performs operations in this order:

1. **role::app_server** (`site-modules/role/manifests/app_server.pp`):
   - Includes `profile::base::base`; its implementation is outside the supplied execution tree.
   - Includes `profile::loadbalancer::haproxy`; its implementation is outside the supplied execution tree.
   - Includes `profile::app::stack`; its implementation is outside the supplied execution tree.
   - Includes `profile::cache::redis`.

2. **profile::cache::redis** (`site-modules/profile/manifests/cache/redis.pp`):
   - Includes `profile_redis_cluster`.
   - Reads the `environment` fact through `fact('environment')`.
   - No additional resources are shown in the supplied execution tree.

3. **profile_redis_cluster** (`site-modules/profile_redis_cluster/manifests/init.pp`):
   - Contains `profile_redis_cluster::install`.
   - The structured analysis does not confirm a PuppetDB query, exported resource, virtual resource, resource collector, or cross-node Redis discovery mechanism.
   - Do not implement Redis Cluster membership, replication, Sentinel, dynamic inventory, or peer discovery solely from this profile name.

4. **profile_redis_cluster::install** (`site-modules/profile_redis_cluster/manifests/install.pp`):
   - Declares class `redis`.
   - The original source review reported the following intended Redis parameters, which must be confirmed against the effective catalog before migration:
     - `bind`: `0.0.0.0`
     - `port`: `6379`
     - `requirepass`: sourced from `profile_redis_cluster::redis_password`
     - `maxmemory`: derived from `profile_redis_cluster::maxmemory_mb`
     - `appendonly`: enabled
     - `appendfsync`: `everysec`
     - `manage_package`: enabled

5. **redis** (`site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/init.pp`):
   - Inherits `redis::params`.
   - The source file for `redis::params` is not included in the preserved file structure or supplied structured analysis.
   - Package names, service names, directory paths, owners, modes, OS-family defaults, and provider behavior attributed to `redis::params` remain unresolved until the dependency source or an effective catalog is inspected.
   - Includes `redis::preinstall`.
   - Includes `redis::install`.
   - Includes `redis::config`.
   - Includes `redis::service`.
   - Applies the following class relationships:
     - `Class['redis::preinstall'] -> Class['redis::install'] -> Class['redis::config']`
     - `Class['redis::config'] ~> Class['redis::service']`
   - A Redis configuration change refreshes the managed Redis service according to the service provider’s refresh behavior.
   - `$instances.each` creates additional Redis instances from entries in the dependency `$instances` hash.
   - No entries in `$instances` are provided by the supplied analysis; no loop iterations can be expanded into verified instance names.
   - `redis::instance['default']` may be created through the dependency default-instance path when `default_install` is enabled.

6. **redis::preinstall** (`site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/preinstall.pp`):
   - Performs conditional Redis repository management when enabled by dependency configuration.
   - Uses `$facts['os']['name']`.
   - Uses `$facts['os']['family']`.
   - The supplied analysis does not establish whether custom repository, PPA, RPM repository, or module-stream management is active.
   - Ansible migration must use the repository configuration observed in the current effective Puppet catalog or on existing managed hosts.

7. **redis::install** (`site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/install.pp`):
   - Manages an OS-dependent Redis package when package management is enabled.
   - May manage a Redis DNF module stream when one is configured by the dependency.
   - Uses `$facts['os']['family']`.
   - The package name and DNF stream state are not verified by the supplied analysis.
   - Ansible migration must install the exact package and preserve the DNF module stream behavior observed on the source platform.

8. **redis::config** (`site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/config.pp`):
   - Manages the Redis configuration directory.
   - Manages the Redis log directory.
   - Manages the Redis working or data directory.
   - May create `redis::instance['default']` when `default_install` is enabled.
   - May create additional named instances from `$instances.each`.
   - Exact paths, ownership, groups, modes, and instance settings are dependency and OS-default dependent and must be collected before migration.

9. **redis::instance** (`site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/instance.pp`):
   - Manages each created Redis instance, including any conditionally created `default` instance and any explicitly configured instances from `$instances`.
   - For an instance titled `default`, applies default-instance conditional behavior.
   - Creates a per-instance log directory only when that directory differs from the class log directory.
   - Creates a per-instance working directory only when that directory differs from the class working directory.
   - May manage a systemd unit file when `manage_service_file` is enabled.
   - Uses template `redis/service_templates/redis.service.epp` for each created instance with `manage_service_file` enabled.
   - May manage a systemd limits drop-in when no service file is managed and ulimit management is enabled.
   - Manages the original Redis configuration file.
   - Runs an `exec` resource to copy the original Redis configuration file to the active instance configuration file.
   - Supports special rendering behavior for Puppet `Deferred` template values; no Deferred values are established by the supplied analysis.

10. **redis::ulimit** (`site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/ulimit.pp`):
    - Runs only when dependency ulimit management is enabled.
    - May manage `/etc/security/limits.d/redis.conf` when Redis is cluster-manager-managed.
    - May manage `/etc/systemd/system/<redis-service>.service.d/limit.conf`.
    - The supplied analysis does not establish concrete ulimit values, service names, or whether ulimit management is enabled.
    - Preserve only values verified from effective Puppet-managed hosts.

11. **Debian-specific Redis defaults**:
    - When `$facts['os']['family'] == 'Debian'`, manages `/etc/default/redis-server`.
    - No equivalent resource is created in the default non-Debian branch.

12. **redis::service** (`site-modules/profile_redis_cluster/migration-dependencies/redis/manifests/service.pp`):
    - Manages an OS-dependent Redis service when dependency service management is enabled.
    - Receives refresh notifications from `Class['redis::config']`.
    - The effective service name, enablement state, provider, and running state must be confirmed from the effective catalog or managed host.

### Required Ansible Ordering

1. Gather facts, including operating system family and distribution.
2. Determine the currently effective Redis package name, service name, package repository behavior, DNF module stream, configuration paths, log paths, data paths, ownership, modes, and systemd overrides from a Puppet-managed host or effective catalog.
3. Configure a DNF module stream only if the current RedHat-family deployment uses one.
4. Install the verified Redis package.
5. Create the verified Redis configuration, log, and data directories using observed ownership and modes.
6. Render the active Redis configuration using only settings confirmed from the effective Puppet catalog.
7. Render a systemd service unit or limits drop-in only when the existing deployment manages a non-standard unit or limits configuration.
8. Run `systemctl daemon-reload` after systemd unit or drop-in changes.
9. Enable and start the verified Redis service.
10. Restart or reload Redis only when its configuration, service unit, or limits configuration changes.

## Variables

**Variable Flow Summary**: The supplied file structure identifies three Hiera data files, but the supplied structured analysis does not provide hierarchy order, lookup results, variable values, types, merge behavior, or effective class parameters. Reported Redis values must be validated through Hiera lookup output or an effective Puppet catalog before migration.

### Variable Definitions

**common.yaml (defaults)** → Migration note: Identified in the file structure, but its `profile_redis_cluster` keys and values are not verified by the supplied structured analysis.
- No verified `profile_redis_cluster` variable values are available.

**environment/production.yaml (environment-specific)** → Migration note: Identified in the file structure, but its `profile_redis_cluster` keys and overrides are not verified by the supplied structured analysis.
- No verified `profile_redis_cluster` variable values are available.

**environment/staging.yaml (environment-specific)** → Migration note: Identified in the file structure, but its `profile_redis_cluster` keys and overrides are not verified by the supplied structured analysis.
- No verified `profile_redis_cluster` variable values are available.

**Manifest defaults** → Migration note: The original plan reported defaults for Redis port, password, memory, and policy; their values and effective precedence require source and catalog confirmation.
- `profile_redis_cluster::redis_port`: reported as `6379` (type: integer; unverified)
- `profile_redis_cluster::redis_password`: reported default `CHANGEME` (type: string; unverified)
- `profile_redis_cluster::maxmemory_mb`: reported default `2048` (type: integer; unverified)
- `profile_redis_cluster::maxmemory_policy`: reported default `allkeys-lru` (type: string; unverified)
- The original plan reported that `maxmemory_policy` is not passed to the `redis` class declaration; confirm this against source before deciding whether to manage Redis eviction policy in Ansible.

### Credentials Migration

- `profile_redis_cluster::redis_password` is a reported Redis `requirepass` input and must be treated as a credential if confirmed by Hiera lookup or the effective catalog.
- The original plan reported plaintext Hiera value `test-redis-password`; this value is not validated by the supplied structured analysis and must not be copied into Ansible defaults or source control.
- Store the confirmed password in Ansible Vault.
- Use `no_log: true` for Ansible tasks that render, validate, or pass the Redis password.
- Restrict Redis configuration file ownership and mode according to the target distribution and the existing managed deployment.

### Variable Migration Summary

- **Common defaults**: Unknown number of verified variables; inspect `data/common.yaml` and run Hiera lookups.
- **OS-specific variables**: No verified profile-specific OS variables.
- **Environment-specific variables**: Unknown; inspect `data/environment/production.yaml` and `data/environment/staging.yaml`.
- **Host-specific variables**: No host-specific variables are identified by the supplied analysis.
- **Encrypted variables**: No encrypted Hiera values are verified. Any confirmed Redis password must be migrated to Ansible Vault.

### Cross-Level Overrides

Variables defined at multiple Hiera levels:
- No cross-level Redis variable overrides or merge strategies are verified by the supplied analysis.
- Confirm lookup precedence and values with commands such as:

```bash
puppet lookup profile_redis_cluster::redis_password --explain
puppet lookup profile_redis_cluster::maxmemory_mb --explain
puppet lookup profile_redis_cluster::redis_port --explain
puppet lookup profile_redis_cluster::maxmemory_policy --explain
```

### Merge Strategy Notes

- Variables using `hash` merge merge hash values from multiple Hiera levels using a shallow merge.
- Variables using `deep` merge recursively merge hash values from multiple Hiera levels.
- Variables using `first` merge use the first matching value found in the hierarchy.
- No merge strategy for `profile_redis_cluster` variables is verified by the supplied analysis.

## Custom Types and Providers

### Custom fact: redis_role

- Source: `site-modules/profile_redis_cluster/lib/facter/redis_role.rb`.
- The file is identified in the preserved file structure, but its implementation is not included in the supplied structured analysis.
- Linux confinement, inspection of `/etc/redis/conf.d/replica.conf`, detection of `replicaof`, and returned role values are unverified source-inspection claims.
- The supplied execution tree does not show consumption of a `redis_role` fact by `profile_redis_cluster` or the Redis dependency.
- Do not reproduce this fact in Ansible unless direct source inspection confirms its behavior and an Ansible consumer requires it.

## Dependencies

**External module dependencies**:
- `puppetlabs-stdlib` version `9.6.0`
- `puppet-redis` version `11.0.0`
- `puppetlabs-apt` version `9.4.0`

**System package dependencies**:
- An OS-dependent Redis package managed by the Forge Redis dependency when package management is enabled.
- A DNF Redis module stream only when configured by the dependency on RedHat-family systems.
- Exact package names and DNF stream state must be verified before migration.

**Service dependencies**:
- `redis::preinstall` precedes `redis::install`.
- `redis::install` precedes `redis::config`.
- `redis::config` notifies `redis::service`.
- Systemd unit or drop-in changes require `systemctl daemon-reload` before restarting the Redis service.
- Redis must be enabled and started only after its configuration is valid.

## Puppet Facts Used

- `environment`
  - Obtained by `fact('environment')` in `profile::cache::redis`.
  - Identifies the Puppet environment.

- `$facts['os']['name']`
  - Used by `redis::preinstall`.
  - Selects operating-system-specific repository or package behavior.

- `$facts['os']['family']`
  - Used by `redis::preinstall`, `redis::install`, and Redis configuration behavior.
  - Controls OS-family-specific package and repository behavior.
  - Controls the Debian-only `/etc/default/redis-server` resource.

## Template Conversion Notes

### `redis/service_templates/redis.service.epp`

- Template source: `redis/service_templates/redis.service.epp`.
- The template receives 10 variables from the dependency.
- The template contains 3 logic blocks.
- It renders once for each created Redis instance whose `manage_service_file` setting is enabled.
- The supplied analysis does not establish which instances are created, whether `manage_service_file` is enabled, or the resulting render count.
- Confirm actual rendered unit files and render counts from an effective catalog or Puppet-managed host before creating an Ansible template.
- Obtain existing units before migration:

```bash
systemctl cat redis
systemctl cat redis-server
```

- Prefer the target distribution’s Redis systemd unit unless the existing Puppet-managed unit contains required non-standard settings.

### Redis server configuration

- The dependency manages Redis configuration through `redis::instance`.
- The original plan reported the following intended configuration lines; validate them against the active configuration and effective catalog before implementing them in Ansible:

```conf
bind 0.0.0.0
port 6379
requirepass <vault-managed secret>
maxmemory 256mb
appendonly yes
appendfsync everysec
```

- Preserve only verified configuration directives.
- Do not add `maxmemory-policy allkeys-lru` unless the active Puppet-managed Redis configuration or effective catalog confirms it.

## Checks for the Migration

**Files to verify**:
- The active Redis configuration file path for every verified Redis instance.
- The original or generated Redis configuration file path for every verified Redis instance.
- The Redis configuration directory.
- The Redis log directory.
- The Redis data or working directory.
- `/etc/default/redis-server` on Debian-family systems.
- `/etc/security/limits.d/redis.conf` when dependency cluster-manager ulimit handling is active.
- `/etc/systemd/system/<redis-service>.service.d/limit.conf` when dependency ulimit handling is active.
- Every managed Redis systemd unit rendered from `redis/service_templates/redis.service.epp`.
- The source and active configuration file paths used by the dependency copy operation.

**Service endpoints to check**:
- The Redis TCP bind address and port for every verified Redis instance.
- The original plan reported TCP port `6379` and bind address `0.0.0.0`; confirm these values before migration.
- No UNIX socket is identified by the supplied structured analysis.

**Templates rendered**:
- `redis/service_templates/redis.service.epp`:
  - Rendered once for every created Redis instance with `manage_service_file` enabled.
  - Exact render count is unverified.
- Redis server configuration:
  - Generated for every created Redis instance.
  - Exact instance names and render count are unverified.

## Pre-flight checks:

```bash
# Gather current Redis package, service, and instance information.
rpm -qa | grep -i '^redis' || dpkg-query -W -f='${binary:Package} ${Version}\n' 'redis*'
systemctl list-unit-files | grep -Ei 'redis'
systemctl list-units --type=service --all | grep -Ei 'redis'

# Identify active Redis listeners and configuration paths.
ss -ltnp | grep -i redis
ps -ef | grep '[r]edis-server'
systemctl cat redis || true
systemctl cat redis-server || true

# Validate Redis configuration files after identifying the active path.
redis-server --version
redis-server <active-redis-config-path> --test-memory 2

# Inspect effective Puppet values before migration.
puppet lookup profile_redis_cluster::redis_password --explain
puppet lookup profile_redis_cluster::maxmemory_mb --explain
puppet lookup profile_redis_cluster::redis_port --explain
puppet lookup profile_redis_cluster::maxmemory_policy --explain

# Inspect Puppet catalog resources to identify Redis instances, paths, and service names.
puppet resource package | grep -i redis
puppet resource service | grep -i redis

# After rollout, run these checks separately for every verified Redis instance.
redis-cli -h <instance-bind-or-loopback-address> -p <instance-port> --no-auth-warning -a '<vault-secret>' PING
redis-cli -h <instance-bind-or-loopback-address> -p <instance-port> --no-auth-warning -a '<vault-secret>' CONFIG GET appendonly
redis-cli -h <instance-bind-or-loopback-address> -p <instance-port> --no-auth-warning -a '<vault-secret>' CONFIG GET appendfsync
redis-cli -h <instance-bind-or-loopback-address> -p <instance-port> --no-auth-warning -a '<vault-secret>' CONFIG GET maxmemory
redis-cli -h <instance-bind-or-loopback-address> -p <instance-port> --no-auth-warning -a '<vault-secret>' INFO persistence
```

- For every verified Redis instance, confirm unauthenticated access is rejected when `requirepass` is configured.
- For every verified Redis instance, confirm authenticated `PING` returns `PONG`.
- Confirm the active Redis listener address and port match the effective Puppet configuration.
- Confirm AOF, `appendfsync`, maximum memory, eviction policy, systemd limits, and service enablement only when those settings are verified from the effective catalog or existing Puppet-managed host.