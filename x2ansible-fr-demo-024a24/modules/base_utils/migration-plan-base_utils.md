---
source-path: site-modules/base_utils
---

# Migration Plan: base_utils

**TLDR**: `base_utils` is a Linux base-host utility component entered by `profile::base::base` when `manage_utils` is enabled. The validated execution flow conditionally manages `/etc/motd` through `base_utils` and iterates over `utility_packages` to install packages. The exact Hiera hierarchy, package values, MOTD template source, file attributes, custom-component behavior, dependency metadata, and credential findings require source validation before they are treated as migration requirements.

## Service Type and Instances

**Service Type**: Base operating-system configuration and utility-package provisioning. `base_utils` does not operate a standalone application daemon.

**Configured Instances**:

- **System MOTD**: Conditional file-management resource.
  - Location/Path: `/etc/motd`
  - Port/Socket: none
  - Key Config: Declared by `base_utils` only when `manage_motd` is enabled. The template source, ownership, group, mode, and rendered content require manifest and template-source validation.

- **Debian utility package set**: Conditional package resources derived from `utility_packages`.
  - Location/Path: system package manager database
  - Port/Socket: none
  - Key Config: The supplied plan proposes `vim`, `wget`, `curl`, `jq`, and `dnsutils`; package values require Hiera-data validation before migration.

- **RedHat utility package set**: Conditional package resources derived from `utility_packages`.
  - Location/Path: system package manager database
  - Port/Socket: none
  - Key Config: The supplied plan proposes `vim-enhanced`, `wget`, `curl`, `jq`, and `bind-utils`; package values require Hiera-data validation before migration.

- **Chrony service**: Related `profile::base::base` branch outside `base_utils`.
  - Location/Path: systemd service unit
  - Port/Socket: NTP service behavior is outside the supplied execution-tree detail.
  - Key Config: The execution tree confirms a Linux-gated Chrony package/service branch controlled by `manage_ntp`. Package name, service attributes, enablement, and runtime state require manifest validation.

- **Rsyslog service**: Related `profile::base::base` branch outside `base_utils`.
  - Location/Path: systemd service unit
  - Port/Socket: Syslog service behavior is outside the supplied execution-tree detail.
  - Key Config: The execution tree confirms a Linux-gated rsyslog package/service branch controlled by `manage_syslog`. Package name, service attributes, enablement, and runtime state require manifest validation.

## File Structure

**MANDATORY: Preserve this section from the original plan.**

```text
site-modules/base_utils/manifests/init.pp
site-modules/profile/manifests/base/base.pp
site-modules/role/manifests/app_server.pp

site-modules/base_utils/data/common.yaml
site-modules/base_utils/data/os/Debian.yaml
site-modules/base_utils/data/os/RedHat.yaml

site-modules/base_utils/lib/facter/base_utils_info.rb
site-modules/base_utils/functions/ensure_value.pp
site-modules/base_utils/functions/normalize_port.pp
site-modules/base_utils/types/ensure_value.pp
site-modules/base_utils/types/log_level.pp
site-modules/base_utils/types/port.pp
site-modules/base_utils/plans/health_check.pp
site-modules/base_utils/plans/rolling_restart.pp
```

**File inventory limitation**:

- The supplied structured analysis reports 101 analyzed files.
- Only the 14 paths above were provided in the original migration plan.
- The remaining 87 analyzed file paths were not supplied and cannot be categorized as in scope or out of scope.
- Obtain the complete analyzed-file inventory before declaring this migration complete, including all manifests, templates, Hiera data, tasks, plans, custom facts, functions, types, metadata files, and credential-related files.

## Module Explanation

The module performs operations in this order:

1. **`role::app_server`** (`site-modules/role/manifests/app_server.pp`):
   - Enters `profile::base::base`.
   - Also enters `profile::loadbalancer::haproxy`, `profile::app::stack`, and `profile::cache::redis`.
   - The load balancer, application-stack, and Redis branches are outside the validated `base_utils` migration scope.

2. **`profile::base::base`** (`site-modules/profile/manifests/base/base.pp`):
   - Evaluates `manage_utils`.
   - Includes `base_utils` when `manage_utils` is enabled.
   - Evaluates Linux-gated branches using `facts['kernel']`.
   - Evaluates the `manage_ntp` branch for Chrony package and service management.
   - Evaluates the `manage_syslog` branch for rsyslog package and service management.
   - The effective values of `manage_utils`, `manage_ntp`, and `manage_syslog` were not included in the supplied structured analysis and must be mapped to Ansible inventory variables.

3. **`base_utils`** (`site-modules/base_utils/manifests/init.pp`):
   - Evaluates `manage_motd`.
   - When `manage_motd` is enabled, declares `file['/etc/motd']`.
   - The template source, destination content source, owner, group, mode, and rendering behavior must be confirmed from `site-modules/base_utils/manifests/init.pp` and the referenced template source.
   - Iterates over `utility_packages` and declares one package resource for every resolved package value.
   - The supplied proposed Debian package expansion is:
     - `package['vim']`
     - `package['wget']`
     - `package['curl']`
     - `package['jq']`
     - `package['dnsutils']`
   - The supplied proposed RedHat package expansion is:
     - `package['vim-enhanced']`
     - `package['wget']`
     - `package['curl']`
     - `package['jq']`
     - `package['bind-utils']`
   - These package lists and their operating-system mappings require Hiera validation before implementation.
   - For platforms with an empty resolved `utility_packages` value, no package resources are declared.
   - Notifications, subscriptions, ordering relationships, virtual resources, exported resources, and collectors require source-level manifest validation before migration conclusions are made.

**Recommended Ansible role flow**:

```yaml
# roles/base_utils/tasks/main.yml
- name: Manage MOTD
  ansible.builtin.template:
    src: "{{ base_utils_motd_template }}"
    dest: /etc/motd
    owner: root
    group: root
    mode: "0644"
  when: base_utils_manage_motd | bool

- name: Install base utility packages
  ansible.builtin.package:
    name: "{{ base_utils_utility_packages }}"
    state: present
  when: base_utils_utility_packages | length > 0
```

```yaml
# Higher-level profile or playbook flow
- name: Apply base utility configuration
  ansible.builtin.include_role:
    name: base_utils
  when: profile_base_manage_utils | bool
```

The MOTD ownership, group, mode, and template name in the example must be aligned with the validated Puppet manifest and ERB template before implementation.

## Variables

**Variable Flow Summary**: The execution tree confirms the use of `manage_utils`, `manage_motd`, `utility_packages`, `manage_ntp`, and `manage_syslog`. The supplied Hiera file paths and proposed values require validation against the actual Hiera hierarchy, lookup options, and data-file contents.

### Variable Definitions

**`site-modules/base_utils/data/common.yaml` (module defaults; proposed mapping pending Hiera validation)** → Migration note: Validate this file against the module Hiera hierarchy before using it as the Ansible default-variable source.

- `base_utils::manage_motd`: proposed value `true` (type: boolean; unverified)
- `base_utils::motd_template`: proposed value `base_utils/motd.erb` (type: string; unverified)
- `base_utils::utility_packages`: proposed value `[]` (type: array of strings; unverified)

**`site-modules/base_utils/data/os/Debian.yaml` (Debian-family override; proposed mapping pending Hiera validation)** → Migration note: Load through Debian inventory group variables only after confirming the hierarchy and package values.

- `base_utils::utility_packages`: proposed value `[vim, wget, curl, jq, dnsutils]` (type: array of strings; unverified)

**`site-modules/base_utils/data/os/RedHat.yaml` (RedHat-family override; proposed mapping pending Hiera validation)** → Migration note: Load through RedHat inventory group variables only after confirming the hierarchy and package values.

- `base_utils::utility_packages`: proposed value `[vim-enhanced, wget, curl, jq, bind-utils]` (type: array of strings; unverified)

**Variables confirmed by execution-tree usage but without supplied Hiera definitions** → Migration note: Define equivalent inventory, group, host, or role variables after reviewing the control-repository Hiera hierarchy.

- `manage_utils` / proposed Ansible variable `profile_base_manage_utils`: type and effective value not supplied.
- `manage_ntp` / proposed Ansible variable `profile_base_manage_ntp`: type and effective value not supplied.
- `manage_syslog` / proposed Ansible variable `profile_base_manage_syslog`: type and effective value not supplied.

### Variable Migration Summary

- **Common defaults**: 3 proposed `base_utils` defaults in the supplied plan; validate against `common.yaml`.
- **OS-specific variables**: 1 proposed package-list override for Debian and 1 proposed package-list override for RedHat; validate against OS data files.
- **Environment-specific variables**: Not evidenced by the supplied structured analysis.
- **Host-specific variables**: Not evidenced by the supplied structured analysis.
- **Encrypted variables**: Not evidenced by the supplied structured analysis; complete credential and eyaml review is required.

### Cross-Level Overrides

Variables requiring Hiera hierarchy validation:

- **`base_utils::utility_packages`**: Proposed as defined in common, Debian, and RedHat data.
  - Proposed Debian value: `[vim, wget, curl, jq, dnsutils]`.
  - Proposed RedHat value: `[vim-enhanced, wget, curl, jq, bind-utils]`.
  - Proposed unmatched-platform value: `[]`.
  - Confirm lookup precedence and whether a control-repository or environment-level override exists.

- **`base_utils::manage_motd`**: Proposed as a common-level value of `true`.
  - Confirm whether this value can be overridden by environment, host, or role data.

- **`base_utils::motd_template`**: Proposed as a common-level value of `base_utils/motd.erb`.
  - Confirm the template path and all override locations.

### Merge Strategy Notes

- The supplied plan proposed `first` lookup behavior for all listed values.
- The structured analysis did not include Hiera lookup options or hierarchy configuration.
- Do not implement list merging, hash merging, or replacement behavior until `hiera.yaml`, module lookup options, and applicable control-repository data are reviewed.
- If `utility_packages` uses Puppet `first` lookup behavior, Ansible variables must replace the complete package list at higher-precedence inventory levels rather than merge lists.

### Proposed Ansible Variable Mapping

```yaml
# roles/base_utils/defaults/main.yml
# Values require validation against Puppet Hiera and manifest sources.
base_utils_manage_motd: true
base_utils_motd_template: motd.j2
base_utils_utility_packages: []
```

```yaml
# group_vars/Debian.yml
# Proposed package list; validate before use.
base_utils_utility_packages:
  - vim
  - wget
  - curl
  - jq
  - dnsutils
```

```yaml
# group_vars/RedHat.yml
# Proposed package list; validate before use.
base_utils_utility_packages:
  - vim-enhanced
  - wget
  - curl
  - jq
  - bind-utils
```

## Custom Types and Providers

The following custom-component paths were identified in the original plan, but their behavior was not included in the supplied structured analysis. Review each source file and every invoked task before implementing compatibility replacements.

- **Custom fact `base_utils_info`** (`site-modules/base_utils/lib/facter/base_utils_info.rb`)
  - Validate supported platforms, returned fact structure, package-detection commands, failure behavior, and uptime behavior.
  - If compatibility is required, implement an Ansible custom fact or fact plugin after source review.

- **Function `base_utils::ensure_value`** (`site-modules/base_utils/functions/ensure_value.pp`)
  - Validate parameter names, types, defaulting behavior, and consumers.
  - Map verified defaulting behavior to Jinja `default()` logic or explicit Ansible variable validation.

- **Function `base_utils::normalize_port`** (`site-modules/base_utils/functions/normalize_port.pp`)
  - Validate accepted input types, coercion behavior, range validation, and consumers.
  - Map verified validation requirements to `ansible.builtin.assert` tasks or role argument specifications.

- **Type alias `Base_utils::Ensure_value`** (`site-modules/base_utils/types/ensure_value.pp`)
  - Validate allowed values and all consumers.
  - Replace with Ansible role argument validation or assertion tasks.

- **Type alias `Base_utils::Log_level`** (`site-modules/base_utils/types/log_level.pp`)
  - Validate accepted syslog severity values and all consumers.
  - Replace with Ansible role argument validation or assertion tasks.

- **Type alias `Base_utils::Port`** (`site-modules/base_utils/types/port.pp`)
  - Validate numeric range and all consumers.
  - Replace with Ansible integer and range validation.

- **Bolt plan `base_utils::health_check`** (`site-modules/base_utils/plans/health_check.pp`)
  - Validate plan parameters, defaults, invoked tasks, result handling, and target-selection behavior.
  - Identify and analyze the referenced `base_utils::check_service` task before migration.

- **Bolt plan `base_utils::rolling_restart`** (`site-modules/base_utils/plans/rolling_restart.pp`)
  - Validate plan parameters, restart sequencing, health-check behavior, delay behavior, failure handling, and target ordering.
  - A likely Ansible implementation is a dedicated play using `serial: 1`, but exact behavior must follow source validation.

## Dependencies

**External module dependencies**:

The following dependency versions were listed in the original plan but were not supported by supplied metadata analysis. Validate against `metadata.json`, `Puppetfile`, modulefiles, and lockfiles before creating Ansible dependency requirements.

- `puppetlabs-stdlib` version `9.7.0`
- `puppetlabs-concat` version `9.0.2`
- `puppetlabs-firewall` version `8.1.0`
- `puppetlabs-vcsrepo` version `6.1.0`
- `puppet-redis` version `11.0.0`
- `puppet-systemd` version `7.1.0`
- `puppetlabs-inifile` version `6.1.1`
- `puppetlabs-apt` version `9.4.0`

**System package dependencies**:

Proposed package dependencies requiring Hiera and manifest validation:

- Debian:
  - `vim`
  - `wget`
  - `curl`
  - `jq`
  - `dnsutils`

- RedHat:
  - `vim-enhanced`
  - `wget`
  - `curl`
  - `jq`
  - `bind-utils`

- Related `profile::base::base` branches:
  - Chrony package and service configuration when `manage_ntp` is enabled on Linux.
  - Rsyslog package and service configuration when `manage_syslog` is enabled on Linux.

**Service dependencies**:

- `base_utils` has no validated standalone service-management resource.
- `profile::base::base` contains validated Linux-gated Chrony and rsyslog branches.
- Validate package-before-service ordering, service enablement, runtime state, notifications, subscriptions, and resource relationships from source manifests.

## Puppet Facts Used

- **`facts['kernel']`**
  - Provides the operating-system kernel name.
  - Used by `profile::base::base` to restrict Chrony and rsyslog branches to Linux.

- **`base_utils_info`**
  - Custom fact source path: `site-modules/base_utils/lib/facter/base_utils_info.rb`.
  - The fact is listed in the supplied file structure, but its values and module consumers require source validation.

## Template Conversion Notes

- **MOTD template referenced by `base_utils`**
  - Destination resource: `/etc/motd`.
  - Puppet render condition: `manage_motd` enabled.
  - The supplied structured analysis does not identify the template path, ERB source content, referenced variables, owner, group, mode, or render count.
  - Inspect `site-modules/base_utils/manifests/init.pp` and the referenced ERB file before creating `roles/base_utils/templates/motd.j2`.
  - Preserve verified static content exactly.
  - Convert verified ERB conditionals to Jinja `{% if %}` blocks.
  - Convert verified ERB iterations to Jinja `{% for %}` blocks.
  - Replace verified Puppet facts with Ansible facts or explicitly managed role variables.
  - Record the validated render count after template analysis. A conditional file resource normally renders once per applicable managed host during an Ansible run, but this must not be treated as equivalent to the Puppet behavior until the source is reviewed.

## PuppetDB Dependencies

**Context**: PuppetDB usage, resource collectors, exported resources, virtual resources, and manifest relationships were not included in the supplied structured analysis.

- Review all in-scope manifests for exported resources (`@@`), virtual resources (`@`), resource collectors (`<<| |>>`), `puppetdb_query()` calls, notifications, subscriptions, and ordering relationships.
- Do not conclude that PuppetDB is unused until this source-level review is complete.

## Credentials

- No credential, encrypted-Hiera, secret-provider, token, password, or private-key analysis was supplied for `base_utils`.
- The original plan stated that `base_utils` contains no secrets and referenced Redis credentials in an out-of-scope branch; neither conclusion is validated by the supplied structured analysis.
- Review all 101 analyzed files, Hiera data, eyaml values, `Sensitive` values, templates, Bolt plans, and external secret-provider integrations before finalizing credential migration.
- If credentials are found in the broader `role::app_server` scope, migrate them to Ansible Vault or an approved external secret manager and use `no_log: true` for tasks that process secret material.

## Checks for the Migration

**Files to verify**:

- `/etc/motd`
  - Verify only when `base_utils_manage_motd` is enabled.
  - Confirm existence, content, owner, group, and mode against the validated Puppet manifest and template source.

- `site-modules/base_utils/manifests/init.pp`
  - Confirm the `manage_motd` conditional.
  - Confirm all `utility_packages` loop behavior.
  - Confirm file attributes, template source, package ensure value, relationships, notifications, and PuppetDB usage.

- `site-modules/profile/manifests/base/base.pp`
  - Confirm `manage_utils`, `manage_ntp`, and `manage_syslog` behavior.
  - Confirm Linux gating using `facts['kernel']`.
  - Confirm Chrony and rsyslog package/service attributes and ordering.

- `site-modules/role/manifests/app_server.pp`
  - Confirm execution entry into `profile::base::base`.
  - Confirm the boundary between `base_utils` and unrelated application, load-balancer, and Redis branches.

- `site-modules/base_utils/data/common.yaml`
- `site-modules/base_utils/data/os/Debian.yaml`
- `site-modules/base_utils/data/os/RedHat.yaml`
  - Confirm values, types, hierarchy position, overrides, and lookup behavior.

- `site-modules/base_utils/lib/facter/base_utils_info.rb`
- `site-modules/base_utils/functions/ensure_value.pp`
- `site-modules/base_utils/functions/normalize_port.pp`
- `site-modules/base_utils/types/ensure_value.pp`
- `site-modules/base_utils/types/log_level.pp`
- `site-modules/base_utils/types/port.pp`
- `site-modules/base_utils/plans/health_check.pp`
- `site-modules/base_utils/plans/rolling_restart.pp`
  - Confirm behavior and identify all referenced task files and dependent source paths.

**Service endpoints to check**:

- **System MOTD**: no network endpoint; verify `/etc/motd`.
- **Debian utility package set**: no network endpoint; verify each validated package through `dpkg-query`.
- **RedHat utility package set**: no network endpoint; verify each validated package through `rpm`.
- **Chrony service**: verify systemd status only when the validated `manage_ntp` branch applies.
- **Rsyslog service**: verify systemd status only when the validated `manage_syslog` branch applies.

**Templates rendered**:

- MOTD template to `/etc/motd`: render count and template source require validation from the Puppet manifest and ERB source.

## Pre-flight checks:

```bash
# Validate operating-system identity for the Debian utility package instance.
cat /etc/os-release

# Debian utility package instance: run only after validating the package list.
dpkg-query -W vim
dpkg-query -W wget
dpkg-query -W curl
dpkg-query -W jq
dpkg-query -W dnsutils

# RedHat utility package instance: run only after validating the package list.
rpm -q vim-enhanced
rpm -q wget
rpm -q curl
rpm -q jq
rpm -q bind-utils

# System MOTD instance: run only when MOTD management is enabled.
test -f /etc/motd
stat -c '%U:%G %a %n' /etc/motd
cat /etc/motd

# Chrony service instance: run only when the validated Linux/manage_ntp branch applies.
systemctl is-active chronyd

# Rsyslog service instance: run only when the validated Linux/manage_syslog branch applies.
systemctl is-active rsyslog

# Validate Ansible idempotence after source and Hiera validation.
ansible-playbook -i inventory base_utils.yml
ansible-playbook -i inventory base_utils.yml
```