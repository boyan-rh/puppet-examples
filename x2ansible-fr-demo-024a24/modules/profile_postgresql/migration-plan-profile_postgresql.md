---
source-path: site-modules/profile_postgresql
---

# Migration Plan: profile_postgresql

**TLDR**: `profile_postgresql` provisions the local `postgresql` service for the application stack when `profile_app_stack::db_host` is `localhost`. It configures the PostgreSQL Global Development Group (PGDG) APT repository, installs PostgreSQL 15, PostgreSQL contrib, and `libpq-dev`, then enables and starts PostgreSQL. `profile_app_stack::database` creates application role `testuser`, database `testdb`, and grants privileges when the database host is local. It also declares `/usr/local/bin/db-backup.sh` and `cron[database_backup]` outside the local-host conditional; the source, schedule, ownership, and exact ordering of these backup resources must be reviewed in the original manifest before Ansible conversion. The module default is PostgreSQL 16, overridden to effective version 15 by higher-priority environment Hiera data.

## Service Type and Instances

**Service Type**: PostgreSQL relational database server, deployed locally as an application dependency.

**Configured Instances**:
- **postgresql**
  - Location/Path: Distribution-managed PostgreSQL configuration and data paths. This module does not declare a PostgreSQL configuration file or cluster data directory.
  - Port/Socket: `localhost:5432`
  - Key Config:
    - PostgreSQL version: `15`
    - PGDG APT repository: `https://apt.postgresql.org/pub/repos/apt`
    - PGDG APT suite: `<distribution-codename>-pgdg`
    - PGDG APT component: `main`
    - Packages: `postgresql-15`, `postgresql-contrib-15`, `libpq-dev`
    - Service: `postgresql`, enabled and running
    - Application database: `testdb`
    - Application role: `testuser`
    - Backup artifact: `/usr/local/bin/db-backup.sh`
    - Backup cron resource: `cron[database_backup]`

## File Structure

```text
site-modules/
├── role/
│   └── manifests/
│       └── app_server.pp
├── profile/
│   └── manifests/
│       └── app/
│           └── stack.pp
├── profile_app_stack/
│   └── manifests/
│       ├── init.pp
│       └── database.pp
└── profile_postgresql/
    ├── data/
    │   ├── common.yaml
    │   └── os/
    │       └── Debian.yaml
    └── manifests/
        ├── init.pp
        ├── install.pp
        ├── repo.pp
        └── service.pp

data/
└── common.yaml

migration-dependencies/
└── apt/
    └── manifests/
        ├── conf.pp
        ├── init.pp
        ├── key.pp
        ├── keyring.pp
        ├── params.pp
        ├── pin.pp
        ├── ppa.pp
        ├── setting.pp
        ├── source.pp
        └── update.pp
```

## Module Explanation

The module performs operations in this order:

1. **`role::app_server`** (`site-modules/role/manifests/app_server.pp`):
   - Includes `profile::app::stack`.
   - Does not directly assign `profile_postgresql`; the PostgreSQL profile is reached through the application-stack database profile.

2. **`profile::app::stack`** (`site-modules/profile/manifests/app/stack.pp`):
   - Includes `profile_app_stack`.
   - References `fact('environment')` to select environment-related application-stack behavior.

3. **`profile_app_stack`** (`site-modules/profile_app_stack/manifests/init.pp`):
   - Declares class order:
     - `profile_app_stack::python`
     - `profile_app_stack::database`
     - `profile_app_stack::app`
     - `profile_app_stack::service`
     - `profile_app_stack::monitoring`
   - The relationship `profile_app_stack::app ~> profile_app_stack::service` notifies the application service when the application class changes.

4. **`profile_app_stack::database`** (`site-modules/profile_app_stack/manifests/database.pp`):
   - Evaluates the condition `db_host == 'localhost'`.
   - The effective value is `localhost`, so the local PostgreSQL branch is active.
   - Under the local-host conditional, includes `profile_postgresql` and declares:
     - `exec[create_db_user]`
     - `exec[create_database]`
     - `exec[grant_db_privileges]`
   - Effective local database inputs:
     - Host: `localhost`
     - Port: `5432`
     - Database: `testdb`
     - Role: `testuser`
     - Role password: `test-db-password`
   - The supplied execution tree shows the following resources outside the `db_host == 'localhost'` conditional:
     - `file[/usr/local/bin/db-backup.sh]`
     - `cron[database_backup]`
   - The supplied execution tree does not expose command strings, guards, ownership, file mode, source/template, cron schedule, or resource relationships for the three `exec` resources, backup file, or backup cron resource.
   - Inspect the original `site-modules/profile_app_stack/manifests/database.pp` implementation before implementing equivalent Ansible tasks, particularly before making backup tasks conditional on a local database host.

5. **`profile_postgresql`** (`site-modules/profile_postgresql/manifests/init.pp`):
   - Uses effective class parameters:
     - Version: `15`
     - Package list:
       - `postgresql-15`
       - `postgresql-contrib-15`
     - Service: `postgresql`
   - Contains `profile_postgresql::repo`.
   - Contains `profile_postgresql::install`.
   - Contains `profile_postgresql::service`.
   - Enforces class ordering:
     - `Class['profile_postgresql::repo'] -> Class['profile_postgresql::install'] -> Class['profile_postgresql::service']`

6. **`profile_postgresql::repo`** (`site-modules/profile_postgresql/manifests/repo.pp`):
   - Includes dependency class `apt`.
   - Declares `apt::source { 'pgdg': }` with:
     - Location: `https://apt.postgresql.org/pub/repos/apt`
     - Release: `<distribution-codename>-pgdg`
     - Repository component: `main`
     - Signing-key ID: `B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8`
     - Signing-key source: `https://www.postgresql.org/media/keys/ACCC4CF8.asc`
   - Resolves the repository suite from Puppet fact `facts['os']['distro']['codename']`.
   - Ansible equivalent: `{{ ansible_distribution_release }}-pgdg`.
   - The `apt::source['pgdg']` defined type materializes:
     - An APT signing-key resource for key ID `B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8`.
     - An APT source-list setting for source `pgdg`.
   - Recommended Ansible implementation:
     - Download and install the PGDG signing key using `ansible.builtin.get_url` and a keyring/dearmor task, or use the distribution-approved `deb822_repository` workflow.
     - Configure `deb https://apt.postgresql.org/pub/repos/apt {{ ansible_distribution_release }}-pgdg main`.
     - Refresh APT metadata after repository or key changes.

7. **`apt::params`** (`migration-dependencies/apt/manifests/params.pp`):
   - Supplies inherited APT module defaults to `apt`.
   - Its effective parameter values are not fully resolvable from the supplied profile Hiera data.
   - Review this manifest during migration if APT directory management, key-management packages, update frequency, or other APT defaults must be preserved.

8. **`apt`** (`migration-dependencies/apt/manifests/init.pp`):
   - Provides the APT dependency behavior used by `profile_postgresql::repo`.
   - May manage APT update state, standard APT directories, signing-key support, and source-list settings through:
     - `migration-dependencies/apt/manifests/update.pp`
     - `migration-dependencies/apt/manifests/conf.pp`
     - `migration-dependencies/apt/manifests/key.pp`
     - `migration-dependencies/apt/manifests/keyring.pp`
     - `migration-dependencies/apt/manifests/pin.pp`
     - `migration-dependencies/apt/manifests/ppa.pp`
     - `migration-dependencies/apt/manifests/setting.pp`
     - `migration-dependencies/apt/manifests/source.pp`
   - This dependency behavior is not profile-specific and must be reviewed if full parity with the existing APT management policy is required.

9. **`profile_postgresql::install`** (`site-modules/profile_postgresql/manifests/install.pp`):
   - Installs `package['postgresql-15']` with `ensure => installed` and a requirement on `Class['profile_postgresql::repo']`.
   - Installs `package['postgresql-contrib-15']` with `ensure => installed` and a requirement on `Class['profile_postgresql::repo']`.
   - Installs `package['libpq-dev']` with `ensure => installed`.
   - No loops occur in this class. The effective package array expands to:
     - `postgresql-15`
     - `postgresql-contrib-15`
   - Ansible must install all three packages after the PGDG repository is configured and APT metadata is refreshed.

10. **`profile_postgresql::service`** (`site-modules/profile_postgresql/manifests/service.pp`):
    - Manages `service['postgresql']`.
    - Ensures the service is running.
    - Enables the service at boot.
    - Requires `Class['profile_postgresql::install']`.
    - No PostgreSQL configuration-file resource notifies this service.
    - Do not unconditionally restart PostgreSQL in Ansible unless package changes, repository changes, or future configuration tasks require a restart.

Required Ansible task order for the local PostgreSQL branch:

```yaml
- Configure PGDG signing key
- Configure PGDG APT repository
- Refresh APT package metadata
- Install postgresql-15
- Install postgresql-contrib-15
- Install libpq-dev
- Enable and start postgresql
- Create application database role testuser
- Create application database testdb
- Grant testuser privileges on testdb
```

The final five application-stack resources are owned by `profile_app_stack::database`:

```yaml
- Create application database role testuser
- Create application database testdb
- Grant testuser privileges on testdb
- Deploy /usr/local/bin/db-backup.sh
- Configure database_backup cron entry
```

The supplied execution tree places the backup file and cron resources outside the local-host conditional. Confirm their intended condition and relationship ordering from `site-modules/profile_app_stack/manifests/database.pp` before implementing the final two Ansible tasks.

## Variables

**Variable Flow Summary**: 29 Hiera entries across three relevant Hiera data files, representing 28 distinct Hiera keys because `profile_postgresql::version` is defined at two hierarchy levels. The effective PostgreSQL version is selected through first-value Hiera precedence: environment `data/common.yaml` overrides the module baseline value.

### Variable Definitions

**data/common.yaml (environment common, higher priority than module data)** → Migration note: Environment-level application-stack configuration and PostgreSQL version override.

- `profile_app_stack::app_name`: `test-app` (type: string)
  - Ansible mapping: `app_stack_app_name: test-app`
- `profile_app_stack::app_repo`: `file:///tmp/test-app-repo` (type: string)
  - Ansible mapping: `app_stack_app_repo: file:///tmp/test-app-repo`
- `profile_app_stack::app_revision`: `master` (type: string)
  - Ansible mapping: `app_stack_app_revision: master`
- `profile_app_stack::app_port`: `8000` (type: integer)
  - Ansible mapping: `app_stack_app_port: 8000`
- `profile_app_stack::app_dir`: `/opt/test-app` (type: string)
  - Ansible mapping: `app_stack_app_dir: /opt/test-app`
- `profile_app_stack::app_user`: `appuser` (type: string)
  - Ansible mapping: `app_stack_app_user: appuser`
- `profile_app_stack::app_group`: `appuser` (type: string)
  - Ansible mapping: `app_stack_app_group: appuser`
- `profile_app_stack::db_host`: `localhost` (type: string)
  - Ansible mapping: `app_stack_db_host: localhost`
- `profile_app_stack::db_port`: `5432` (type: integer)
  - Ansible mapping: `app_stack_db_port: 5432`
- `profile_app_stack::db_name`: `testdb` (type: string)
  - Ansible mapping: `app_stack_db_name: testdb`
- `profile_app_stack::db_user`: `testuser` (type: string)
  - Ansible mapping: `app_stack_db_user: testuser`
- `profile_app_stack::db_password`: `test-db-password` (type: string; credential)
  - Ansible mapping: `app_stack_db_password`
  - Store only in Ansible Vault.
- `profile_app_stack::worker_count`: `2` (type: integer)
  - Ansible mapping: `app_stack_worker_count: 2`
- `profile_app_stack::worker_class`: `sync` (type: string)
  - Ansible mapping: `app_stack_worker_class: sync`
- `profile_app_stack::max_requests`: `1000` (type: integer)
  - Ansible mapping: `app_stack_max_requests: 1000`
- `profile_app_stack::graceful_timeout`: `30` (type: integer)
  - Ansible mapping: `app_stack_graceful_timeout: 30`
- `profile_app_stack::log_dir`: `/var/log/test-app` (type: string)
  - Ansible mapping: `app_stack_log_dir: /var/log/test-app`
- `profile_app_stack::log_level`: `info` (type: string)
  - Ansible mapping: `app_stack_log_level: info`
- `profile_app_stack::secret_key`: `test-secret-key` (type: string; credential)
  - Ansible mapping: `app_stack_secret_key`
  - Store only in Ansible Vault.
- `profile_postgresql::version`: `15` (type: string)
  - Ansible mapping: `postgresql_version: '15'`
  - Overrides the role default PostgreSQL version.

The following environment variables are not referenced by the supplied PostgreSQL execution path but must be preserved if the surrounding application-stack profile is migrated:

- `profile_app_stack::python_version`: `python3` (type: string)
  - Ansible mapping: `app_stack_python_version: python3`
- `profile_app_stack::pip_packages`: `[]` (type: array)
  - Ansible mapping: `app_stack_pip_packages: []`

**site-modules/profile_postgresql/data/common.yaml (module common baseline)** → Migration note: Base PostgreSQL role default for all supported nodes.

- `profile_postgresql::version`: `16` (type: string)
  - Ansible mapping: `postgresql_version: '16'`
  - Place in `roles/profile_postgresql/defaults/main.yml`.

**site-modules/profile_postgresql/data/os/Debian.yaml (Debian OS-specific)** → Migration note: Load only for Debian-family targets. Place equivalent values in `group_vars/Debian.yml`, role OS-specific variables, or an explicit platform mapping.

- `profile_postgresql::package_names`: `["postgresql-%{lookup('profile_postgresql::version')}", "postgresql-contrib-%{lookup('profile_postgresql::version')}"]` (type: array)
  - Effective resolved value: `["postgresql-15", "postgresql-contrib-15"]`
  - Ansible mapping:

```yaml
postgresql_package_names:
  - "postgresql-{{ postgresql_version }}"
  - "postgresql-contrib-{{ postgresql_version }}"
```

- `profile_postgresql::service_name`: `postgresql` (type: string)
  - Ansible mapping: `postgresql_service_name: postgresql`
- `profile_postgresql::repo_location`: `https://apt.postgresql.org/pub/repos/apt` (type: string)
  - Ansible mapping: `postgresql_repo_location: https://apt.postgresql.org/pub/repos/apt`
- `profile_postgresql::repo_release`: `%{facts.os.distro.codename}-pgdg` (type: string)
  - Effective resolved value: `<distribution-codename>-pgdg`
  - Ansible mapping: `postgresql_repo_release: "{{ ansible_distribution_release }}-pgdg"`
- `profile_postgresql::repo_key_id`: `B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8` (type: string)
  - Ansible mapping: `postgresql_repo_key_id: B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8`
- `profile_postgresql::repo_key_source`: `https://www.postgresql.org/media/keys/ACCC4CF8.asc` (type: string)
  - Ansible mapping: `postgresql_repo_key_source: https://www.postgresql.org/media/keys/ACCC4CF8.asc`

Recommended Ansible variable placement:

```yaml
# roles/profile_postgresql/defaults/main.yml
postgresql_version: '16'

# group_vars/Debian.yml
postgresql_package_names:
  - "postgresql-{{ postgresql_version }}"
  - "postgresql-contrib-{{ postgresql_version }}"
postgresql_service_name: postgresql
postgresql_repo_location: https://apt.postgresql.org/pub/repos/apt
postgresql_repo_release: "{{ ansible_distribution_release }}-pgdg"
postgresql_repo_key_id: B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8
postgresql_repo_key_source: https://www.postgresql.org/media/keys/ACCC4CF8.asc

# group_vars/postgresql.yml or group_vars/app_stack.yml
postgresql_version: '15'
app_stack_db_host: localhost
app_stack_db_port: 5432
app_stack_db_name: testdb
app_stack_db_user: testuser

# group_vars/app_stack/vault.yml
app_stack_db_password: "<vault-encrypted value>"
app_stack_secret_key: "<vault-encrypted value>"
```

### Variable Migration Summary

- **Common defaults**: 1 Hiera entry from `site-modules/profile_postgresql/data/common.yaml`, providing the PostgreSQL 16 module baseline.
- **OS-specific variables**: 6 Hiera entries from `site-modules/profile_postgresql/data/os/Debian.yaml`.
- **Environment-specific variables**: 22 Hiera entries from `data/common.yaml`, including the PostgreSQL version override and two application-stack variables not referenced by the supplied PostgreSQL execution path.
- **Host-specific variables**: 0 variables supplied.
- **Encrypted variables**: 0 Hiera-encrypted variables supplied.
- **Plaintext credentials requiring secure migration**: 2:
  - `profile_app_stack::db_password` → `app_stack_db_password` in Ansible Vault.
  - `profile_app_stack::secret_key` → `app_stack_secret_key` in Ansible Vault.

### Cross-Level Overrides

Variables defined at multiple Hiera levels:

- **`profile_postgresql::version`**:
  - Defined in `site-modules/profile_postgresql/data/common.yaml` as `16`.
  - Defined in `data/common.yaml` as `15`.
  - Merge strategy: `first` / normal scalar Hiera precedence.
  - Effective value: `15`.
  - Ansible equivalent: role default `postgresql_version: '16'`, overridden by an inventory or group variable `postgresql_version: '15'`.

### Merge Strategy Notes

- Variables using `hash` merge: No hash-merged variables are identified in the supplied Hiera data.
- Variables using `deep` merge: No deep-merged variables are identified in the supplied Hiera data.
- Variables using `first` (default): Scalar values use first-value precedence. `profile_postgresql::version` is resolved using this strategy.

## Dependencies

**External module dependencies**:

- `puppetlabs-apt` version `9.4.0`
  - Used directly by `profile_postgresql::repo`.
  - Provides PGDG APT source, signing-key, source-list, and APT update behavior.
- `puppetlabs-stdlib` version `9.7.0`
  - Used transitively by `puppetlabs-apt` for package and key support.
- `puppetlabs-concat` version `9.0.2`
- `puppetlabs-firewall` version `8.1.3`
- `puppetlabs-vcsrepo` version `6.1.0`
- `puppet-redis` version `11.0.0`
- `puppet-systemd` version `7.1.0`
- `puppetlabs-inifile` version `6.1.1`

Only `puppetlabs-apt` and transitive `puppetlabs-stdlib` behavior are in the supplied PostgreSQL profile execution path.

**System package dependencies**:

- `postgresql-15`
- `postgresql-contrib-15`
- `libpq-dev`
- `python3-psycopg2`, if required by the selected `community.postgresql` module version.
- `gnupg`, if required by the selected Debian-family PGDG key-management implementation.

**Service dependencies**:

- The PGDG signing key and PGDG APT source must exist before PostgreSQL packages are installed.
- PostgreSQL packages must be installed before `postgresql` is enabled and started.
- The `postgresql` service must be running before database role, database, and privilege operations execute.
- Local PostgreSQL provisioning and the three database `exec` resources apply only when `app_stack_db_host` is `localhost`.
- The supplied execution tree declares the backup file and cron resources outside that local-host condition; verify the original manifest before applying an Ansible condition.

## Puppet Facts Used

- `facts['os']['family']`
  - Identifies the operating-system family.
  - Used by the APT module to reject non-Debian systems.
  - Ansible equivalent: `ansible_os_family`.
  - Constrain this role to Debian-family systems or implement explicit platform mappings.

- `facts['os']['name']`
  - Identifies the OS name, such as Debian or Ubuntu.
  - Used by the APT module to select `gnupg` package behavior.
  - Ansible equivalent: `ansible_distribution`.

- `facts['os']['release']['full']`
  - Provides the full OS version.
  - Used by optional APT PPA compatibility logic in the dependency module.
  - Ansible equivalent: `ansible_distribution_version`.

- `facts['os']['distro']['codename']`
  - Provides the distribution release codename.
  - Resolves the PGDG repository suite as `<codename>-pgdg`.
  - Ansible equivalent: `ansible_distribution_release`.

- `facts['apt_update_last_success']`
  - Provides the timestamp of the last successful APT metadata refresh.
  - Used by `apt::update` to determine whether an APT update is required according to configured frequency.
  - Ansible equivalent: use `ansible.builtin.apt` with `update_cache: true` and an appropriate `cache_valid_time`.

- `fact('environment')`
  - Provides the Puppet environment name.
  - Referenced by `profile::app::stack`.
  - Ansible equivalent: an inventory group, `environment` variable, or deployment-stage variable.

## Template Conversion Notes

No templates are referenced by `profile_postgresql`.

The complete local database execution path includes `file[/usr/local/bin/db-backup.sh]`, owned by `profile_app_stack::database`. Its source or template, content, mode, owner, group, conditional behavior, and handler relationships are not included in the supplied execution tree. Review the original manifest before converting this resource.

## Checks for the Migration

**Files to verify**:

- PGDG repository source-list file created by the Ansible repository task.
- PGDG signing key or keyring created by the Ansible key-management task.
- `/usr/local/bin/db-backup.sh`
- Package-managed PostgreSQL configuration and data files in default locations for the target Debian release.

**Service endpoints to check**:

- `postgresql` service unit.
- `localhost:5432`.

**Templates rendered**:

- `profile_postgresql`: 0 templates rendered.
- `/usr/local/bin/db-backup.sh`: rendering method is unknown from the supplied execution tree and must be confirmed from `site-modules/profile_app_stack/manifests/database.pp`.

## Pre-flight checks:

```bash
# Verify the supported operating system and identify the PGDG suite.
. /etc/os-release
printf '%s-pgdg\n' "$VERSION_CODENAME"

# Confirm PGDG repository metadata can be retrieved.
apt-get update

# Confirm exact PostgreSQL package versions.
dpkg-query -W postgresql-15 postgresql-contrib-15 libpq-dev

# Confirm the named postgresql service is enabled and active.
systemctl is-enabled postgresql
systemctl is-active postgresql

# Confirm the postgresql instance accepts connections on localhost:5432.
pg_isready -h localhost -p 5432

# Confirm application database resources after local-database tasks run.
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = 'testuser';"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = 'testdb';"

# Confirm testuser privileges on testdb after privilege migration.
sudo -u postgres psql -d testdb -tAc "SELECT has_database_privilege('testuser', 'testdb', 'CONNECT');"

# Validate the backup artifact and inspect the current user's cron entries
# after backup source, mode, ownership, schedule, and conditions are migrated.
test -x /usr/local/bin/db-backup.sh
crontab -l
```