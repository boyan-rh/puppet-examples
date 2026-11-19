---
source-path: site-modules/profile_haproxy
---

# Migration Plan: profile_haproxy

**TLDR**: `profile_haproxy` manages the HAProxy load-balancer profile through installation, configuration, service, and firewall classes, with optional discovery functionality. The structured analysis validates the manifest execution flow, named resources, template references, error-page iteration, firewall branches, and optional PuppetDB exported-resource collection. Hiera hierarchy, literal Hiera values, resource attributes, backend definitions, and several custom-component implementations were not available in the validated analysis and must be exported and verified before implementing an equivalent Ansible role.

## Service Type and Instances

**Service Type**: HAProxy Layer 4/7 load balancer with HTTP, HTTPS, optional statistics, backend fragments, optional firewall management, and optional service discovery.

**Configured Instances**:
- **HAProxy**: Primary HAProxy service managed by `profile_haproxy`.
  - Location/Path: Main configuration path and configuration directory are Hiera-driven but their effective literal values were not provided in the validated analysis.
  - Port/Socket:
    - HTTP: `80/tcp`
    - HTTPS: `443/tcp`
    - Statistics port: Hiera-driven; a previously reported `9001/tcp` value is unverified and must be confirmed from effective Hiera data.
    - HAProxy runtime socket and PID paths are not validated from the structured execution-tree analysis.
  - Key Config:
    - Package resource title: `haproxy`
    - Main configuration template: `profile_haproxy/haproxy.cfg.erb`
    - Backend configuration template: `profile_haproxy/backend.conf.epp`
    - Static error pages: `503.http` and `408.http`
    - Effective backends, TLS settings, statistics settings, credentials, and service settings require Hiera export and source-level validation.

## File Structure

```text
### Manifests

- `site-modules/role/manifests/haproxy.pp`
- `site-modules/profile/manifests/base/base.pp`
- `site-modules/profile/manifests/loadbalancer/haproxy.pp`
- `site-modules/profile_haproxy/manifests/init.pp`
- `site-modules/profile_haproxy/manifests/install.pp`
- `site-modules/profile_haproxy/manifests/config.pp`
- `site-modules/profile_haproxy/manifests/service.pp`
- `site-modules/profile_haproxy/manifests/firewall.pp`
- `site-modules/profile_haproxy/manifests/discover.pp`
- `site-modules/base_utils/manifests/init.pp`

### Data

- `data/common.yaml`
- `data/environment/production.yaml`
- `data/environment/staging.yaml`
- `site-modules/profile_haproxy/data/common.yaml`
- `site-modules/profile_haproxy/data/os/Debian.yaml`
- `site-modules/profile_haproxy/data/os/RedHat.yaml`
- `site-modules/profile_haproxy/data/environment/production.yaml`
- `site-modules/profile_haproxy/data/environment/staging.yaml`
- `site-modules/profile_haproxy/data/datacenter/dc1_fra.yaml`
- `site-modules/profile_haproxy/data/cluster/haproxy_prod_fra.yaml`
- `site-modules/profile_haproxy/data/nodes/lb01.fra.example.com.yaml`
- `site-modules/base_utils/data/common.yaml`
- `site-modules/base_utils/data/os/Debian.yaml`
- `site-modules/base_utils/data/os/RedHat.yaml`

### Templates and Static Content

- `profile_haproxy/haproxy.cfg.erb`
- `profile_haproxy/backend.conf.epp`
- `profile_haproxy/haproxy_errors/503.http`
- `profile_haproxy/haproxy_errors/408.http`

### Custom Components

- `site-modules/profile_haproxy/lib/facter/haproxy_version.rb`
- `site-modules/base_utils/functions/normalize_port.pp`
```

## Module Explanation

The module performs operations in this order:

1. **`role::haproxy`** (`site-modules/role/manifests/haproxy.pp`):
   - Runs an `exec['defaults']` resource when the kernel fact lower-cases to `linux`.
   - Includes `::profile::base::base`.
   - Includes `::profile::loadbalancer::haproxy`.
   - Enforces `Class['::profile::base::base'] -> Class['::profile::loadbalancer::haproxy']`.
   - The attributes and command of `exec['defaults']` were not provided by the structured analysis and must be reviewed before migration.

2. **`::profile::base::base`** (`site-modules/profile/manifests/base/base.pp`):
   - Includes `base_utils` when base utility management is enabled.
   - Manages `package['chrony']` and `service['chronyd']` when NTP management is enabled and the kernel fact is exactly `Linux`.
   - Manages `package['rsyslog']` and `service['rsyslog']` when syslog management is enabled and the kernel fact is exactly `Linux`.
   - Package and service attributes, enablement controls, and effective values require source and Hiera validation.

3. **`base_utils`** (`site-modules/base_utils/manifests/init.pp`):
   - Manages `file['/etc/motd']` when MOTD management is enabled.
   - Iterates over the configured utility-package array and creates package resources.
   - The configured utility-package names were not available in the validated analysis and cannot be expanded. Export the effective Debian and RedHat package arrays before creating the Ansible package loop.
   - The MOTD template and resource attributes require source-level validation.

4. **`::profile::loadbalancer::haproxy`** (`site-modules/profile/manifests/loadbalancer/haproxy.pp`):
   - Includes `profile_haproxy`.
   - Reads `fact('environment')`.
   - The validated execution tree does not expose additional wrapper resources or explain how the environment value is used.

5. **`profile_haproxy`** (`site-modules/profile_haproxy/manifests/init.pp`):
   - Declares `profile_haproxy::install`.
   - Declares `profile_haproxy::config`.
   - Declares `profile_haproxy::service`.
   - Declares `profile_haproxy::firewall`.
   - When discovery is disabled, the validated relationship is:
     ```text
     profile_haproxy::install
       -> profile_haproxy::config
       ~> profile_haproxy::service
     ```
   - When discovery is enabled, the validated alternate relationship is:
     ```text
     profile_haproxy::install
       -> profile_haproxy::config
       -> profile_haproxy::discover
       ~> profile_haproxy::service
     ```
   - `profile_haproxy::firewall` is contained without a validated explicit ordering relationship to installation, configuration, or service management.
   - The effective value of `discovery_enabled` was not available in the validated Hiera analysis.

6. **`profile_haproxy::install`** (`site-modules/profile_haproxy/manifests/install.pp`):
   - Manages `package['haproxy']`.
   - Manages additional package resources when the configured extra-package collection is non-empty.
   - Manages an HAProxy group and user whose names are Hiera-driven.
   - Manages the Hiera-driven HAProxy configuration directory.
   - Manages the `<config_dir>/conf.d` directory.
   - Manages `file['/var/lib/haproxy']`.
   - Declares `exec['haproxy_selinux_connect']` when SELinux management is enabled.
   - Resource attributes, directory ownership, modes, SELinux command content, package state, and effective Hiera values were not provided by the validated execution tree.

7. **`profile_haproxy::config`** (`site-modules/profile_haproxy/manifests/config.pp`):
   - Manages the Hiera-driven main HAProxy configuration file using `profile_haproxy/haproxy.cfg.erb`.
   - Iterates over the configured backend collection and renders a backend fragment using `profile_haproxy/backend.conf.epp`.
   - Backend names and definitions were not available in the validated analysis; they must be exported from the effective Hiera data before backend rendering can be implemented.
   - Manages the error directory and the following validated static error-page files:
     - `<config_dir>/errors/503.http`
     - `<config_dir>/errors/408.http`
   - Optionally manages `<config_dir>/conf.d/stick-tables.cfg` when stick-table functionality is enabled.
   - Main configuration, backend fragments, and stick-table content notify the service class according to the validated execution flow.
   - Resource attributes, backend values, stick-table values, and literal destination paths require source and Hiera validation.

8. **`profile_haproxy::service`** (`site-modules/profile_haproxy/manifests/service.pp`):
   - Manages `file['/etc/systemd/system/haproxy.service.d']`.
   - Manages `file['/etc/systemd/system/haproxy.service.d/override.conf']`.
   - Declares `exec['haproxy_systemd_reload']`.
   - Manages the Hiera-driven HAProxy service resource.
   - Declares `exec['haproxy_config_check']`.
   - Manages `file['/etc/logrotate.d/haproxy']`.
   - The validated execution tree confirms the resources and relationships but does not provide service state, systemd override content, logrotate content, validation command, ownership, modes, or notification attributes. Review the manifest source before reproducing these details in Ansible.

9. **`profile_haproxy::firewall`** (`site-modules/profile_haproxy/manifests/firewall.pp`):
   - Supports validated firewalld, UFW, no-firewall, and unknown-provider branches.
   - Firewalld branch:
     - Declares resources for `80/tcp`.
     - Declares resources for `443/tcp`.
     - Declares a statistics-port resource when statistics are enabled.
     - Declares `exec['firewalld_reload']`.
   - UFW branch:
     - Manages `package['ufw']`.
     - Declares `exec['ufw_allow_http']`.
     - Declares `exec['ufw_allow_https']`.
     - Declares `exec['ufw_allow_stats']` when statistics are enabled.
     - Declares `exec['ufw_enable']`.
   - No-firewall branch creates no firewall resources.
   - Unknown-provider branch emits a Puppet notification.
   - The provider, zone, statistics enablement, statistics port, commands, guards, and package attributes require effective Hiera and source-level validation.

10. **`profile_haproxy::discover`** (`site-modules/profile_haproxy/manifests/discover.pp`):
    - Declares an exported `@@haproxy::balancermember` resource.
    - Collects `Haproxy::Balancermember <| listening_service == 'webservers' |>`.
    - Iterates over `$app_servers` and declares local `haproxy::balancermember` resources.
    - Application-server names, source of `$app_servers`, member parameters, and discovery enablement were not provided in the validated analysis.
    - The structured analysis does not confirm a `puppetdb_query()` call, an explicit PuppetDB query string, or environment/class filtering. Do not implement an asserted query until the source analysis confirms it.

## Variables

**Variable Flow Summary**: The validated execution tree confirms that `profile_haproxy` uses Hiera-driven configuration and conditional behavior, but it does not provide Hiera hierarchy order, YAML contents, merge strategies, effective values, encrypted values, or target-node lookup results. A complete Hiera export is a migration prerequisite.

### Variable Definitions

**Required Hiera-to-Ansible export** → Migration note: The following files are listed in the original module inventory but their contents were not available in the validated analysis. Export each effective lookup with its hierarchy level, value type, redaction status, merge behavior, and target-node result.

- `data/common.yaml`
- `data/environment/production.yaml`
- `data/environment/staging.yaml`
- `site-modules/profile_haproxy/data/common.yaml`
- `site-modules/profile_haproxy/data/os/Debian.yaml`
- `site-modules/profile_haproxy/data/os/RedHat.yaml`
- `site-modules/profile_haproxy/data/environment/production.yaml`
- `site-modules/profile_haproxy/data/environment/staging.yaml`
- `site-modules/profile_haproxy/data/datacenter/dc1_fra.yaml`
- `site-modules/profile_haproxy/data/cluster/haproxy_prod_fra.yaml`
- `site-modules/profile_haproxy/data/nodes/lb01.fra.example.com.yaml`
- `site-modules/base_utils/data/common.yaml`
- `site-modules/base_utils/data/os/Debian.yaml`
- `site-modules/base_utils/data/os/RedHat.yaml`

**Expected `profile_haproxy` mapping inputs** → Migration note: These inputs are inferred from resource titles, templates, and conditional branches. Their literal values and defining hierarchy levels are unverified.

- `profile_haproxy::package_name`: value unavailable (type: string)
- `profile_haproxy::config_dir`: value unavailable (type: string)
- `profile_haproxy::config_file`: value unavailable (type: string)
- `profile_haproxy::service_name`: value unavailable (type: string)
- `profile_haproxy::user`: value unavailable (type: string)
- `profile_haproxy::group`: value unavailable (type: string)
- `profile_haproxy::stats_enabled`: value unavailable (type: boolean)
- `profile_haproxy::stats_port`: value unavailable (type: integer or string requiring normalization)
- `profile_haproxy::stats_uri`: value unavailable (type: string)
- `profile_haproxy::stats_user`: value unavailable (type: string)
- `profile_haproxy::stats_password`: value unavailable; treat as a secret (type: encrypted string or external secret reference)
- `profile_haproxy::global_maxconn`: value unavailable (type: integer)
- `profile_haproxy::client_timeout`: value unavailable (type: string)
- `profile_haproxy::server_timeout`: value unavailable (type: string)
- `profile_haproxy::connect_timeout`: value unavailable (type: string)
- `profile_haproxy::retries`: value unavailable (type: integer)
- `profile_haproxy::ssl_enabled`: value unavailable (type: boolean)
- `profile_haproxy::ssl_cert_path`: value unavailable (type: string or certificate reference)
- `profile_haproxy::ssl_key_path`: value unavailable; treat as a secret reference (type: encrypted string or external secret reference)
- `profile_haproxy::ssl_ciphers`: value unavailable (type: string)
- `profile_haproxy::ssl_min_version`: value unavailable (type: string)
- `profile_haproxy::log_server`: value unavailable (type: string)
- `profile_haproxy::log_facility`: value unavailable (type: string)
- `profile_haproxy::log_level`: value unavailable (type: string)
- `profile_haproxy::backends`: value unavailable (type: hash)
- Firewall provider, firewall zone, extra packages, SELinux enablement, stick-table settings, and discovery enablement: values unavailable.

**Expected `base_utils` mapping inputs** → Migration note: Values and source hierarchy are unverified.

- `base_utils::manage_motd`: value unavailable (type: boolean)
- `base_utils::motd_template`: value unavailable (type: string)
- `base_utils::utility_packages`: value unavailable (type: array)

### Variable Migration Summary

- **Common defaults**: Unknown until the control-repository and module Hiera data are exported.
- **OS-specific variables**: Unknown until Debian and RedHat Hiera data are exported.
- **Environment-specific variables**: Unknown until production and staging Hiera data are exported.
- **Host-specific variables**: Unknown until node-specific Hiera data is exported.
- **Encrypted variables**: At minimum, protect statistics authentication and TLS private-key data as Ansible Vault values or external secret-manager references. Their Puppet storage format and effective values are unverified.

### Cross-Level Overrides

Variables requiring effective-value validation before Ansible implementation:

- **HAProxy package name**: Determine the defining Hiera level and effective package value.
- **HAProxy configuration directory and file**: Determine effective literal paths.
- **HAProxy service name, user, and group**: Determine effective values.
- **Statistics enablement, port, URI, user, and password**: Determine effective values and secret source.
- **TLS enablement, certificate path, key path, ciphers, and minimum version**: Determine effective values and secret-handling requirements.
- **Maximum connections, timeouts, retries, logging settings, stick-table settings, firewall settings, and discovery settings**: Determine effective values.
- **Backend hash**: Determine the complete effective backend collection, backend names, server lists, and merge behavior.

### Merge Strategy Notes

- The validated execution-tree analysis does not establish whether any Hiera key uses `first`, `hash`, or `deep` merge.
- Do not assume that `profile_haproxy::backends` uses a deep merge until the Hiera configuration and lookup options are exported.
- If `profile_haproxy::backends` is confirmed to use Puppet deep merge, reproduce it explicitly in Ansible with recursive `combine` operations before rendering backend files.
- Normal Ansible variable precedence replaces dictionaries and must not be relied upon to reproduce Puppet hash merging.

## Custom Types and Providers

### Custom type: `haproxy::balancermember`

- Referenced by `site-modules/profile_haproxy/manifests/discover.pp`.
- Used as both an exported resource type and a locally declared resource type.
- Exported resources are collected through `Haproxy::Balancermember <| listening_service == 'webservers' |>`.
- The custom type definition, source file, parameters, provider implementation, and local resource attributes were not included in the validated analysis.
- Ansible migration approach:
  - Replace the collected-member pattern with inventory groups, CMDB data, or an authoritative service-discovery API.
  - Build explicit backend member lists before rendering HAProxy backend fragments.
  - Do not attempt to emulate Puppet exported-resource collection unless PuppetDB remains the authoritative discovery source.

### Custom fact: `haproxy_version`

- File listed in the original inventory: `site-modules/profile_haproxy/lib/facter/haproxy_version.rb`.
- Its implementation, supported operating systems, command behavior, and version-parsing logic were not included in the validated analysis.
- If HAProxy version is required by the Ansible role, collect it explicitly with a non-changing command task and validate the parsing expression against the Puppet fact source.

### Custom Puppet function: `base_utils::normalize_port`

- File listed in the original inventory: `site-modules/base_utils/functions/normalize_port.pp`.
- Its implementation and call sites were not included in the validated analysis.
- If firewall port normalization is required, use an explicit Ansible integer conversion only after confirming the Puppet function behavior and accepted input formats.

## Dependencies

**External module dependencies**:

- `puppetlabs-stdlib` version `9.7.0`
- `puppetlabs-concat` version `9.0.2`
- `puppetlabs-firewall` version `8.1.3`

**System package dependencies**:

- `haproxy` is confirmed by a named package resource.
- `chrony` is conditionally managed by `::profile::base::base`.
- `rsyslog` is conditionally managed by `::profile::base::base`.
- `ufw` is managed by the UFW firewall branch.
- Additional HAProxy packages may be configured, but their names were not available in the validated analysis.

**Service dependencies**:

- `::profile::base::base` completes before `::profile::loadbalancer::haproxy`.
- HAProxy installation precedes HAProxy configuration.
- HAProxy configuration precedes service notification.
- When discovery is enabled, discovery runs after configuration and before service notification.
- Systemd override management triggers a daemon reload through `exec['haproxy_systemd_reload']`.
- Source-level validation is required to confirm the exact service restart, reload, validation, and subscription behavior.

## Puppet Facts Used

- `kernel`
  - Used by `role::haproxy` for Linux-specific behavior.
  - Used by `::profile::base::base` for Linux-specific NTP and syslog management.
- `environment`
  - Read by `::profile::loadbalancer::haproxy` through `fact('environment')`.
  - Its purpose is not exposed in the validated execution tree.
- `networking.fqdn`
  - Referenced by the discovery behavior for HAProxy member identity.
- `networking.ip`
  - Referenced by the discovery behavior for HAProxy member addressing.
- `haproxy_version`
  - Listed as a custom fact in the original inventory.
  - Its implementation and direct use in this execution path are unverified.
- Any additional facts used by templates, Hiera hierarchy, custom types, or undisclosed source logic must be identified through complete source analysis.

## Template Conversion Notes

### `profile_haproxy/haproxy.cfg.erb`

- Destination: Hiera-driven main HAProxy configuration file.
- Render count: 1 render per managed HAProxy node.
- The validated analysis identifies 21 referenced variables and 3 Ruby logic blocks.
- The complete variable map was not supplied; only partial mappings can be inferred from the class and template context.
- Migration blocker: identify all 21 referenced variables, their types, defaults, and effective values before finalizing the Jinja2 template.
- Convert all validated Ruby logic blocks to Jinja2 conditional or iteration blocks.
- Store any statistics password, TLS private key, or secret-derived value in Ansible Vault or an external secret manager.
- Apply `no_log: true` to tasks that render secret-bearing configuration.

### `profile_haproxy/backend.conf.epp`

- Destination: `<config_dir>/conf.d/<backend-name>.cfg`.
- Render count: one render for each effective backend entry.
- The actual backend names and total render count are unknown because the effective backend data was not included in the validated analysis.
- The validated analysis identifies 11 referenced variables and 3 logic blocks.
- Migration blocker: identify all 11 referenced variables and export all effective backend definitions before converting the template.
- Validate the complete HAProxy configuration after rendering every changed backend fragment.

### Static error content

- `profile_haproxy/haproxy_errors/503.http`:
  - Destination: `<config_dir>/errors/503.http`
  - Copy count: 1 per managed HAProxy node.
- `profile_haproxy/haproxy_errors/408.http`:
  - Destination: `<config_dir>/errors/408.http`
  - Copy count: 1 per managed HAProxy node.
- Use `ansible.builtin.copy` unless source inspection establishes that the error content requires variable substitution.

## PuppetDB Dependencies

**Context**: `profile_haproxy::discover` uses an optional PuppetDB exported-resource collection pattern. The validated analysis confirms exported-resource declaration, resource collection, and iteration over `$app_servers`, but does not establish how `$app_servers` is populated.

- **Exported Resources** (`@@`):
  - Resource type: `haproxy::balancermember`.
  - The resource is exported by `profile_haproxy::discover`.
  - Migration note: replace cross-node exported-resource data sharing with inventory, CMDB, or service-discovery data supplied before HAProxy configuration rendering.

- **Resource Collectors** (`<<| |>>`):
  - Collector: `Haproxy::Balancermember <| listening_service == 'webservers' |>`.
  - Filter condition: `listening_service == 'webservers'`.
  - Migration note: identify the authoritative source of application-server membership and construct explicit Ansible backend lists from that source.

- **PuppetDB Queries**:
  - No `puppetdb_query()` call or query text is validated by the supplied execution-tree analysis.
  - Migration note: do not implement query-specific replacement logic until the discover manifest source identifies the source and filtering logic for `$app_servers`.

- **Host Identity Data**:
  - Discovery references `networking.fqdn` and `networking.ip`.
  - Migration note: use `ansible_fqdn`, selected gathered network facts, explicitly managed host variables, or CMDB-provided addresses after validating Puppet-side member parameter behavior.

## Checks for the Migration

**Files to verify**:

- Effective main HAProxy configuration file path.
- Effective HAProxy configuration directory.
- Effective `<config_dir>/conf.d` directory.
- `<config_dir>/errors/503.http`.
- `<config_dir>/errors/408.http`.
- `<config_dir>/conf.d/stick-tables.cfg` when stick tables are enabled.
- One `<config_dir>/conf.d/<backend-name>.cfg` file for every backend name exported from effective Hiera data.
- `/var/lib/haproxy`.
- `/etc/systemd/system/haproxy.service.d`.
- `/etc/systemd/system/haproxy.service.d/override.conf`.
- `/etc/logrotate.d/haproxy`.
- `/etc/motd` when base MOTD management is enabled.

**Service endpoints to check**:

- HAProxy HTTP listener: `80/tcp`.
- HAProxy HTTPS listener: `443/tcp`.
- HAProxy statistics listener: verify the effective configured port only when statistics are enabled.
- HAProxy runtime socket: verify only after confirming its configured path from the service manifest.
- HAProxy PID file: verify only after confirming its configured path from the service manifest.

**Templates rendered**:

- `profile_haproxy/haproxy.cfg.erb`:
  - Render count: 1 per HAProxy node.
- `profile_haproxy/backend.conf.epp`:
  - Render count: one per effective backend.
  - Exact count: blocked pending effective backend export.
- `profile_haproxy/haproxy_errors/503.http`:
  - Copy count: 1 per HAProxy node.
- `profile_haproxy/haproxy_errors/408.http`:
  - Copy count: 1 per HAProxy node.
- Stick-table fragment:
  - Render count: 1 per HAProxy node when stick-table functionality is enabled.

## Pre-flight checks:

```bash
# HAProxy instance: HAProxy
# Replace placeholders only with values validated from effective Hiera and manifest source.

# Confirm required package and binary availability.
rpm -q haproxy 2>/dev/null || dpkg-query -W -f='${Status}\n' haproxy 2>/dev/null
haproxy -v

# Validate the effective HAProxy configuration before service restart.
haproxy -c -f <main-config-path> -f <config-dir>/conf.d/

# Reload systemd only when the validated override file is managed.
systemctl daemon-reload

# Verify the effective HAProxy service name and state.
systemctl enable --now <haproxy-service-name>
systemctl status <haproxy-service-name> --no-pager

# Verify required frontend listeners for the HAProxy instance.
ss -ltnp | grep -E ':(80|443)\b'

# Verify the statistics listener only when statistics are enabled.
ss -ltnp | grep -E ':<effective-stats-port>\b'

# Verify runtime socket and PID paths after confirming their effective configured values.
test -S <haproxy-runtime-socket>
test -f <haproxy-pid-path>

# Verify static error files.
test -f <config-dir>/errors/503.http
test -f <config-dir>/errors/408.http

# Verify every exported backend fragment after effective backend names are known.
find <config-dir>/conf.d -maxdepth 1 -type f -name '*.cfg' -print

# Firewalld verification when the validated provider is firewalld.
firewall-cmd --zone=<firewall-zone> --query-port=80/tcp
firewall-cmd --zone=<firewall-zone> --query-port=443/tcp
firewall-cmd --zone=<firewall-zone> --query-port=<effective-stats-port>/tcp

# UFW verification when the validated provider is ufw.
ufw status

# SELinux verification when SELinux management is validated as enabled.
getsebool haproxy_connect_any

# Statistics authentication verification only when statistics are enabled.
# Retrieve credentials from Ansible Vault or an external secret manager.
curl --fail --user '<stats-user>:<stats-password>' \
  "http://127.0.0.1:<effective-stats-port><stats-uri>"
```