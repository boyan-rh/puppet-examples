---
source-path: site-modules/profile_app_stack
---

# Migration Plan: profile_app_stack

**TLDR**: `profile_app_stack` deploys the Python web application `test-app` from `file:///tmp/test-app-repo` to `/opt/test-app`, runs it as `appuser` through a systemd service on TCP port `8000`, provisions the local PostgreSQL `testdb` database, runs Alembic migrations after Git checkout changes, and schedules database backup and HTTP health-check jobs. Production nodes additionally install Prometheus node exporter and Pushgateway and schedule metrics pushes. Most effective values are sourced from the higher-priority control-repository `data/common.yaml`; `log_max_size` and `log_rotate_count` remain sourced from module fallback data. Effective database and application secrets are plaintext and must be migrated to Ansible Vault.

## Service Type and Instances

**Service Type**: Python application stack with a systemd-managed web service, local PostgreSQL database, Git deployment, Python virtual environment, scheduled backups, health checks, and production-only Prometheus monitoring.

**Configured Instances**:

- **test-app**: Python application deployment and systemd service.
  - Location/Path: `/opt/test-app`
  - Repository: `file:///tmp/test-app-repo`
  - Revision: `master`
  - Port/Socket: TCP `8000`
  - Process user/group: `appuser:appuser`
  - Virtual environment: `/opt/test-app/venv`
  - Environment file: `/opt/test-app/.env`
  - Systemd unit: `/etc/systemd/system/test-app.service`
  - Logs: `/var/log/test-app`
  - Key Config:
    - Workers: `2`
    - Worker class: `sync`
    - Maximum requests: `1000`
    - Graceful timeout: `30`
    - Log level: `info`

- **PostgreSQL testdb**: Local PostgreSQL application database.
  - Location/Path: Local PostgreSQL server at `localhost`
  - Port/Socket: TCP `5432`
  - Database: `testdb`
  - Application role: `testuser`
  - PostgreSQL version requested: `15`
  - Backup script: `/usr/local/bin/db-backup.sh`
  - Backup schedule: daily at `02:30` as `root`

- **Prometheus monitoring**: Production-only monitoring resources.
  - Packages: `prometheus-node-exporter`, `prometheus-pushgateway`
  - Node exporter service: `prometheus-node-exporter`
  - Metrics push schedule: every five minutes as `appuser`
  - Application health-check schedule: every two minutes as `root`

## File Structure

### Entry-point and wrapper manifests

- `site-modules/role/manifests/app_server.pp`
- `site-modules/profile/manifests/app/stack.pp`

### profile_app_stack manifests

- `site-modules/profile_app_stack/manifests/init.pp`
- `site-modules/profile_app_stack/manifests/python.pp`
- `site-modules/profile_app_stack/manifests/database.pp`
- `site-modules/profile_app_stack/manifests/app.pp`
- `site-modules/profile_app_stack/manifests/service.pp`
- `site-modules/profile_app_stack/manifests/monitoring.pp`

### PostgreSQL profile manifests reached for a local database

- `site-modules/profile_postgresql/manifests/init.pp`
- `site-modules/profile_postgresql/manifests/repo.pp`
- `site-modules/profile_postgresql/manifests/install.pp`
- `site-modules/profile_postgresql/manifests/service.pp`

### APT dependency manifests reached while configuring the PostgreSQL repository

- `migration-dependencies/apt/manifests/init.pp`
- `migration-dependencies/apt/manifests/params.pp`
- `migration-dependencies/apt/manifests/update.pp`
- `migration-dependencies/apt/manifests/conf.pp`
- `migration-dependencies/apt/manifests/setting.pp`
- `migration-dependencies/apt/manifests/source.pp`
- `migration-dependencies/apt/manifests/key.pp`
- `migration-dependencies/apt/manifests/keyring.pp`
- `migration-dependencies/apt/manifests/pin.pp`
- `migration-dependencies/apt/manifests/ppa.pp`

### Hiera data files

- `data/common.yaml`
- `site-modules/profile_app_stack/data/common.yaml`
- `site-modules/profile_app_stack/data/environment/production.yaml`
- `site-modules/profile_app_stack/data/environment/staging.yaml`

### Referenced module files not present in the supplied directory listing

These file contents must be located or recreated before completing the Ansible role:

- `profile_app_stack/logrotate.conf.erb`
- `profile_app_stack/app.env.erb`
- `profile_app_stack/app.service.epp`
- `puppet:///modules/profile_app_stack/backup.sh`
- `puppet:///modules/profile_app_stack/healthcheck.sh`

## Module Explanation

The module performs operations in this order:

1. **role::app_server** (`site-modules/role/manifests/app_server.pp`):
   - Includes `profile::base::base`, `profile::loadbalancer::haproxy`, `profile::app::stack`, and `profile::cache::redis`.
   - Only `profile::app::stack` is analyzed in this plan.
   - Puppet includes do not impose explicit containment or ordering between these profiles.
   - Ansible must explicitly order base, HAProxy, application-stack, and Redis roles where service dependencies require it.

2. **profile::app::stack** (`site-modules/profile/manifests/app/stack.pp`):
   - Reads `fact('environment')` into the optional `environment_name` parameter.
   - Declares `profile_app_stack`.
   - Does not pass or otherwise use `environment_name` in `profile_app_stack`.

3. **profile_app_stack** (`site-modules/profile_app_stack/manifests/init.pp`):
   - Resolves application and database configuration through Hiera.
   - Computes a database URL through `profile_app_stack::app_db_url(testuser, db_password, localhost, 5432, testdb)`.
   - Contains the following classes in declared execution order:
     - `profile_app_stack::python`
     - `profile_app_stack::database`
     - `profile_app_stack::app`
     - `profile_app_stack::service`
     - `profile_app_stack::monitoring`
   - Applies the following ordering and notification chain:
     - `Class['profile_app_stack::python'] -> Class['profile_app_stack::database']`
     - `Class['profile_app_stack::database'] -> Class['profile_app_stack::app']`
     - `Class['profile_app_stack::app'] ~> Class['profile_app_stack::service']`
     - `Class['profile_app_stack::service'] -> Class['profile_app_stack::monitoring']`
   - Ansible sequence:
     1. Install Python packages and create the `appuser` group, account, log directory, and logrotate configuration.
     2. Configure the PGDG APT repository, install PostgreSQL packages, start PostgreSQL, create `testuser`, create `testdb`, grant privileges, and install the backup script and cron job.
     3. Create `/opt/test-app`, check out the Git repository, create the virtual environment, install requirements, render `.env`, install the health-check script, and run Alembic migrations after checkout changes when `migrations/env.py` exists.
     4. Render the systemd unit, reload systemd, enable, and start `test-app`.
     5. Configure the application health-check cron on every node and configure Prometheus resources only for production inventory members.
   - The implementation of `profile_app_stack::app_db_url` was not supplied. Locate the function before migration and preserve its exact URI scheme, escaping, and password encoding behavior.
   - Generate the derived database URL in memory with `no_log: true`; do not write it to facts, debug output, or non-encrypted variables.

4. **profile_app_stack::python** (`site-modules/profile_app_stack/manifests/python.pp`):
   - Installs the following packages:
     - `<python_version>`
     - `<python_version>-pip`
     - `<python_version>-venv`
     - `<python_version>-dev`
     - `git`
     - `build-essential`
   - Creates group `appuser` as a system group.
   - Creates user `appuser` as a system user with:
     - Primary group: `appuser`
     - Home: `/opt/test-app`
     - Shell: `/bin/bash`
     - Home creation disabled
   - Creates `/var/log/test-app` with owner and group `appuser:appuser` and mode `0755`.
   - Renders `profile_app_stack/logrotate.conf.erb` to `/etc/logrotate.d/test-app` with owner `root:root` and mode `0644`.
   - Template render count: `1`.
   - Logrotate template variables:
     - `app_name=test-app`
     - `log_dir=/var/log/test-app`
     - `log_max_size=100M`
     - `log_rotate_count=7`
   - `profile_app_stack::python_version` is required but has no resolved effective value in the supplied Hiera analysis. Define and verify `app_stack_python_version` before implementation.
   - Preserve the missing logrotate template’s rotation targets, cadence, compression behavior, missing-file behavior, create directives, ownership, and post-rotation behavior.

5. **profile_app_stack::database** (`site-modules/profile_app_stack/manifests/database.pp`):
   - The local PostgreSQL branch is active because `profile_app_stack::db_host` is `localhost`.

   **profile_postgresql** (`site-modules/profile_postgresql/manifests/init.pp`):
   - Contains `profile_postgresql::repo`, `profile_postgresql::install`, and `profile_postgresql::service`.
   - Enforces:
     - `Class['profile_postgresql::repo'] -> Class['profile_postgresql::install']`
     - `Class['profile_postgresql::install'] -> Class['profile_postgresql::service']`

   **profile_postgresql::repo** (`site-modules/profile_postgresql/manifests/repo.pp`):
   - Includes `apt`.
   - Configures `apt::source { 'pgdg': }`.
   - Requires the following unresolved values before migration:
     - `profile_postgresql::repo_location`
     - `profile_postgresql::repo_release`
     - `profile_postgresql::repo_key_id`
     - `profile_postgresql::repo_key_source`

   **apt** (`migration-dependencies/apt/manifests/init.pp`):
   - Includes inherited OS-specific defaults from `apt::params` (`migration-dependencies/apt/manifests/params.pp`).
   - `apt::params` supplies APT operating-system defaults, paths, package names, repository defaults, and APT settings used by the APT classes. Inspect and retain all values used by the PGDG repository configuration.
   - Uses `exec { 'apt_update': }` to conditionally refresh APT package indexes according to the configured update frequency and `apt_update_last_success`.
   - Configures the PGDG source, source-list setting, and PGDG signing key.
   - Installs `gnupg` on Debian or Ubuntu when key management requires it.
   - Optional APT configuration, proxy, keyring, pin, PPA, authorization, source, and configuration branches have no supplied effective inputs. Configure only the PGDG repository and signing key unless current host policy requires additional settings.

   **profile_postgresql::install** (`site-modules/profile_postgresql/manifests/install.pp`):
   - Installs every package in `profile_postgresql::package_names`.
   - Installs `libpq-dev`.
   - The exact `profile_postgresql::package_names` array is unresolved. Define and verify the target distribution’s PostgreSQL 15 server and client package names before implementation.

   **profile_postgresql::service** (`site-modules/profile_postgresql/manifests/service.pp`):
   - Enables and starts `profile_postgresql::service_name`.
   - The service name is unresolved. Define and verify the target distribution’s PostgreSQL 15 service unit before implementation.

   **Local database resources**:
   - Creates PostgreSQL role `testuser` with the secret database password.
   - Creates database `testdb` owned by `testuser`.
   - Grants all privileges on `testdb` to `testuser`.
   - Installs `/usr/local/bin/db-backup.sh` from `puppet:///modules/profile_app_stack/backup.sh`.
   - Sets backup-script owner and group to `root:appuser` and mode to `0750`.
   - Creates cron job `database_backup`:
     - User: `root`
     - Command: `/usr/local/bin/db-backup.sh testdb localhost`
     - Schedule: `02:30` daily
   - Use `community.postgresql.postgresql_user` and `community.postgresql.postgresql_db` as `postgres`; do not interpolate database credentials into shell commands.
   - Protect role-creation and credential-bearing tasks with `no_log: true`.
   - Source or reconstruct `backup.sh` before migration because it determines required packages, backup destination, retention, credentials, permissions, and restore-validation behavior.

6. **profile_app_stack::app** (`site-modules/profile_app_stack/manifests/app.pp`):
   - Creates `/opt/test-app` with owner and group `appuser:appuser` and mode `0755`.
   - Checks out Git repository:
     - Destination: `/opt/test-app`
     - Source: `file:///tmp/test-app-repo`
     - Revision: `master`
     - User: `appuser`
   - Creates `/opt/test-app/venv` by running `<python_version> -m venv /opt/test-app/venv` as `appuser`.
   - Installs Python requirements with `/opt/test-app/venv/bin/pip install -r /opt/test-app/requirements.txt` as `appuser`.
   - The `$pip_packages.each` loop runs zero times because the effective `pip_packages` value is `[]`.
   - No individual `install_pip_<package>` resources are created.
   - Python dependencies are installed exclusively from `/opt/test-app/requirements.txt`.
   - If a future non-empty package list is defined, create one idempotent Ansible pip task for each exact package name after virtualenv creation.
   - Renders `profile_app_stack/app.env.erb` to `/opt/test-app/.env` with owner and group `appuser:appuser` and mode `0600`.
   - Template render count: `1`.
   - Environment template variables:
     - `app_name=test-app`
     - `app_port=8000`
     - `db_url=<derived secret-bearing database URL>`
     - `secret_key=<Ansible Vault secret>`
     - `log_level=info`
     - `log_dir=/var/log/test-app`
     - `worker_count=2`
     - `db_host=localhost`
   - Installs `/usr/local/bin/app-healthcheck.sh` from `puppet:///modules/profile_app_stack/healthcheck.sh` with owner and group `root:root` and mode `0755`.
   - Runs `/opt/test-app/venv/bin/python -m alembic upgrade head` as `appuser` in `/opt/test-app` only after a Git checkout change and only when `/opt/test-app/migrations/env.py` exists.
   - Passes `DATABASE_URL=<derived secret-bearing database URL>` to migrations.
   - Protect environment rendering and migration tasks with `no_log: true`.
   - Preserve notification behavior:
     - Git checkout changes trigger Alembic migrations when `migrations/env.py` exists.
     - Requirements installation changes trigger the service restart behavior.
     - `.env` changes trigger a `test-app` restart.

7. **profile_app_stack::service** (`site-modules/profile_app_stack/manifests/service.pp`):
   - Renders `profile_app_stack/app.service.epp` to `/etc/systemd/system/test-app.service`.
   - Unit owner and group: `root:root`.
   - Unit mode: `0644`.
   - Template render count: `1`.
   - Systemd template variables:
     - `app_name=test-app`
     - `app_dir=/opt/test-app`
     - `app_user=appuser`
     - `app_group=appuser`
     - `app_port=8000`
     - `worker_count=2`
     - `worker_class=sync`
     - `max_requests=1000`
     - `graceful_timeout=30`
     - `log_dir=/var/log/test-app`
     - `log_level=info`
   - Unit-file changes notify `systemd_daemon_reload`, which runs `systemctl daemon-reload`.
   - Enables and starts service `test-app`.
   - The service subscribes to `/opt/test-app/.env`; `.env` changes restart the service.
   - Ensure systemd daemon reload occurs before enabling or starting a newly created or changed unit.
   - Inspect the missing EPP template before conversion and preserve `ExecStart`, environment-file usage, logging options, restart policy, assembled command arguments, and conditional systemd directives.

8. **profile_app_stack::monitoring** (`site-modules/profile_app_stack/manifests/monitoring.pp`):
   - Declares virtual resources on every node:
     - Package `prometheus-node-exporter`
     - Service `prometheus-node-exporter`
     - Package `prometheus-pushgateway`
     - Cron `push_app_metrics`
   - When Puppet fact `environment` is exactly `production`, realizes:
     - Package `prometheus-node-exporter`
     - Service `prometheus-node-exporter`
     - Package `prometheus-pushgateway`
     - Cron `push_app_metrics`
   - Production cron `push_app_metrics`:
     - User: `appuser`
     - Command: `/usr/local/bin/app-healthcheck.sh --push-metrics`
     - Schedule: every five minutes
   - When environment is not `production`, do not install or enable Prometheus packages and do not create the metrics-push cron job.
   - Always creates cron `app_health_check`:
     - User: `root`
     - Command: `/usr/local/bin/app-healthcheck.sh http://localhost:8000/health`
     - Schedule: every two minutes
   - In Ansible, use production inventory group membership, such as `'production' in group_names`, to conditionally manage Prometheus resources.

## Variables

**Variable Flow Summary**: 24 distinct `profile_app_stack` and PostgreSQL Hiera keys were identified across four supplied Hiera data files. Scalar lookups use first-value behavior. Most effective runtime values come from the higher-priority `data/common.yaml`; `profile_app_stack::log_max_size` and `profile_app_stack::log_rotate_count` are sourced from `site-modules/profile_app_stack/data/common.yaml` because they are not overridden in the control repository. No hash or deep merge behavior was identified.

### Variable Definitions

**data/common.yaml (control-repository defaults; highest applicable source)** → Migration note: Primary effective configuration for the current deployment. Migrate secret values to Ansible Vault.

- `profile_app_stack::app_name`: `test-app` (type: string)
- `profile_app_stack::app_repo`: `file:///tmp/test-app-repo` (type: string)
- `profile_app_stack::app_revision`: `master` (type: string)
- `profile_app_stack::app_port`: `8000` (type: integer)
- `profile_app_stack::app_dir`: `/opt/test-app` (type: string)
- `profile_app_stack::app_user`: `appuser` (type: string)
- `profile_app_stack::app_group`: `appuser` (type: string)
- `profile_app_stack::db_host`: `localhost` (type: string)
- `profile_app_stack::db_port`: `5432` (type: integer)
- `profile_app_stack::db_name`: `testdb` (type: string)
- `profile_app_stack::db_user`: `testuser` (type: string)
- `profile_app_stack::db_password`: `<plaintext secret>` (type: string; migrate to Ansible Vault as `app_stack_db_password`)
- `profile_app_stack::worker_count`: `2` (type: integer)
- `profile_app_stack::worker_class`: `sync` (type: string)
- `profile_app_stack::max_requests`: `1000` (type: integer)
- `profile_app_stack::graceful_timeout`: `30` (type: integer)
- `profile_app_stack::log_dir`: `/var/log/test-app` (type: string)
- `profile_app_stack::log_level`: `info` (type: string)
- `profile_app_stack::secret_key`: `<plaintext secret>` (type: string; migrate to Ansible Vault as `app_stack_secret_key`)
- `profile_postgresql::version`: `15` (type: string)

**site-modules/profile_app_stack/data/common.yaml (module fallback)** → Migration note: Lower-priority fallback data. Most values are overridden by `data/common.yaml`; the log rotation values below remain effective because the control repository does not define them.

- `profile_app_stack::app_name`: value present but overridden by `test-app` in `data/common.yaml` (type: string)
- `profile_app_stack::app_repo`: value present but overridden by `file:///tmp/test-app-repo` in `data/common.yaml` (type: string)
- `profile_app_stack::app_revision`: value present but overridden by `master` in `data/common.yaml` (type: string)
- `profile_app_stack::app_port`: value present but overridden by `8000` in `data/common.yaml` (type: integer)
- `profile_app_stack::app_dir`: value present but overridden by `/opt/test-app` in `data/common.yaml` (type: string)
- `profile_app_stack::app_user`: value present but overridden by `appuser` in `data/common.yaml` (type: string)
- `profile_app_stack::app_group`: value present but overridden by `appuser` in `data/common.yaml` (type: string)
- `profile_app_stack::db_host`: value present but overridden by `localhost` in `data/common.yaml` (type: string)
- `profile_app_stack::db_port`: value present but overridden by `5432` in `data/common.yaml` (type: integer)
- `profile_app_stack::db_name`: value present but overridden by `testdb` in `data/common.yaml` (type: string)
- `profile_app_stack::db_user`: value present but overridden by `testuser` in `data/common.yaml` (type: string)
- `profile_app_stack::db_password`: `ENC[PKCS7,...]` (type: encrypted string; overridden by the effective plaintext secret)
- `profile_app_stack::worker_count`: value present but overridden by `2` in `data/common.yaml` (type: integer)
- `profile_app_stack::worker_class`: value present but overridden by `sync` in `data/common.yaml` (type: string)
- `profile_app_stack::max_requests`: value present but overridden by `1000` in `data/common.yaml` (type: integer)
- `profile_app_stack::graceful_timeout`: value present but overridden by `30` in `data/common.yaml` (type: integer)
- `profile_app_stack::log_dir`: value present but overridden by `/var/log/test-app` in `data/common.yaml` (type: string)
- `profile_app_stack::log_level`: value present but overridden by `info` in `data/common.yaml` (type: string)
- `profile_app_stack::python_version`: value present but not resolved in the supplied effective Hiera analysis (type not supplied; define and verify as `app_stack_python_version`)
- `profile_app_stack::pip_packages`: value present but no effective non-empty list supplied (type: array; effective behavior is `[]`)
- `profile_app_stack::log_max_size`: `100M` (type: string; effective module fallback value)
- `profile_app_stack::log_rotate_count`: `7` (type: integer; effective module fallback value)

**site-modules/profile_app_stack/data/environment/production.yaml (module production data; overridden)** → Migration note: Preserve as production inventory/group variables only if the control-repository hierarchy is redesigned to permit environment overrides.

- `profile_app_stack::app_revision`: `v2.4.1` (type: string; overridden by `master`)
- `profile_app_stack::worker_count`: `8` (type: integer; overridden by `2`)
- `profile_app_stack::max_requests`: `5000` (type: integer; overridden by `1000`)
- `profile_app_stack::log_level`: `warning` (type: string; overridden by `info`)
- `profile_app_stack::db_host`: `db-primary.prod.internal` (type: string; overridden by `localhost`)
- `profile_app_stack::db_port`: `5432` (type: integer; overridden by `5432`)
- `profile_app_stack::secret_key`: `ENC[PKCS7,...ProdSecret]` (type: encrypted string; overridden by the effective plaintext secret)

**site-modules/profile_app_stack/data/environment/staging.yaml (module staging data; overridden)** → Migration note: Preserve as staging inventory/group variables only if hierarchy behavior is intentionally changed. Replace the plaintext secret with an Ansible Vault value.

- `profile_app_stack::app_revision`: `main` (type: string; overridden by `master`)
- `profile_app_stack::worker_count`: `1` (type: integer; overridden by `2`)
- `profile_app_stack::max_requests`: `100` (type: integer; overridden by `1000`)
- `profile_app_stack::log_level`: `debug` (type: string; overridden by `info`)
- `profile_app_stack::db_host`: `localhost` (type: string; overridden by the same effective value)
- `profile_app_stack::secret_key`: `staging-not-secret-at-all` (type: plaintext string; overridden by the effective plaintext secret; migrate to Ansible Vault if retained)

### Variable Migration Summary

- **Common defaults**: 20 keys from `data/common.yaml`; 19 application values and PostgreSQL version are effective under the current hierarchy.
- **Module fallback variables**: 4 additional keys from `site-modules/profile_app_stack/data/common.yaml`; `log_max_size` and `log_rotate_count` are effective fallback values, while `python_version` and `pip_packages` require explicit migration decisions.
- **OS-specific variables**: 0 supplied.
- **Environment-specific variables**: 13 module-level values across production and staging; all are overridden by the current control-repository hierarchy.
- **Host-specific variables**: 0 supplied.
- **Encrypted variables**: 2 EYAML values:
  - Fallback `profile_app_stack::db_password`
  - Production `profile_app_stack::secret_key`
- **Plaintext secrets requiring secure migration**: 3 supplied plaintext secret values:
  - Effective `profile_app_stack::db_password` in `data/common.yaml`
  - Effective `profile_app_stack::secret_key` in `data/common.yaml`
  - Staging `profile_app_stack::secret_key` in `environment/staging.yaml`, if retained
- **Ansible Vault mapping**:
  - `profile_app_stack::db_password` → `app_stack_db_password`
  - `profile_app_stack::secret_key` → `app_stack_secret_key`
  - Derived database URL → generated at runtime from Vault data with `no_log: true`

### Cross-Level Overrides

Variables defined at multiple Hiera levels:

- **`profile_app_stack::app_name`**: defined in control common and module common; merge strategy: first; effective value: `test-app`.
- **`profile_app_stack::app_repo`**: defined in control common and module common; merge strategy: first; effective value: `file:///tmp/test-app-repo`.
- **`profile_app_stack::app_revision`**: defined in control common, module common, production, and staging; merge strategy: first; effective value: `master`.
- **`profile_app_stack::app_port`**: defined in control common and module common; merge strategy: first; effective value: `8000`.
- **`profile_app_stack::app_dir`**: defined in control common and module common; merge strategy: first; effective value: `/opt/test-app`.
- **`profile_app_stack::app_user`**: defined in control common and module common; merge strategy: first; effective value: `appuser`.
- **`profile_app_stack::app_group`**: defined in control common and module common; merge strategy: first; effective value: `appuser`.
- **`profile_app_stack::db_host`**: defined in control common, module common, production, and staging; merge strategy: first; effective value: `localhost`.
- **`profile_app_stack::db_port`**: defined in control common, module common, and production; merge strategy: first; effective value: `5432`.
- **`profile_app_stack::db_name`**: defined in control common and module common; merge strategy: first; effective value: `testdb`.
- **`profile_app_stack::db_user`**: defined in control common and module common; merge strategy: first; effective value: `testuser`.
- **`profile_app_stack::db_password`**: defined in control common and module common; merge strategy: first; effective value: control-repository plaintext secret.
- **`profile_app_stack::worker_count`**: defined in control common, module common, production, and staging; merge strategy: first; effective value: `2`.
- **`profile_app_stack::worker_class`**: defined in control common and module common; merge strategy: first; effective value: `sync`.
- **`profile_app_stack::max_requests`**: defined in control common, module common, production, and staging; merge strategy: first; effective value: `1000`.
- **`profile_app_stack::graceful_timeout`**: defined in control common and module common; merge strategy: first; effective value: `30`.
- **`profile_app_stack::log_dir`**: defined in control common and module common; merge strategy: first; effective value: `/var/log/test-app`.
- **`profile_app_stack::log_level`**: defined in control common, module common, production, and staging; merge strategy: first; effective value: `info`.
- **`profile_app_stack::secret_key`**: defined in control common, production, and staging; merge strategy: first; effective value: control-repository plaintext secret.
- **`profile_app_stack::log_max_size`**: defined only in module common; merge strategy: first; effective value: `100M`.
- **`profile_app_stack::log_rotate_count`**: defined only in module common; merge strategy: first; effective value: `7`.

### Merge Strategy Notes

- Variables use `first` lookup behavior: the first value found in the active Hiera hierarchy wins.
- No `hash` merge behavior was identified.
- No `deep` merge behavior was identified.
- Preserve current precedence with Ansible defaults, group variables, host variables, and vaulted variables. Do not silently activate currently overridden production or staging values.

## Dependencies

**External module dependencies**:

- `puppetlabs-stdlib` version `9.7.0`
- `puppetlabs-concat` version `9.0.2`
- `puppetlabs-firewall` version `8.1.3`
- `puppetlabs-vcsrepo` version `6.1.0`
- `puppet-redis` version `11.0.0`
- `puppet-systemd` version `7.1.0`
- `puppetlabs-inifile` version `6.1.1`
- `puppetlabs-apt` version `9.4.0`

**Ansible collection and module dependencies**:

- `ansible.builtin.git`
- `ansible.builtin.group`
- `ansible.builtin.user`
- `ansible.builtin.file`
- `ansible.builtin.template`
- `ansible.builtin.copy`
- `ansible.builtin.apt`
- `ansible.builtin.apt_repository` or `ansible.builtin.deb822_repository`
- `ansible.builtin.get_url`
- `ansible.builtin.pip`
- `ansible.builtin.systemd`
- `ansible.builtin.cron`
- `community.postgresql.postgresql_user`
- `community.postgresql.postgresql_db`

**System package dependencies**:

- Verified from manifests:
  - `git`
  - `build-essential`
  - `libpq-dev`
  - `gnupg` on Debian or Ubuntu when PGDG signing-key management requires it
  - `prometheus-node-exporter` on production nodes only
  - `prometheus-pushgateway` on production nodes only
- Require explicit target-OS verification before deployment:
  - `<python_version>`
  - `<python_version>-pip`
  - `<python_version>-venv`
  - `<python_version>-dev`
  - PostgreSQL package names from `profile_postgresql::package_names`
  - PostgreSQL service name from `profile_postgresql::service_name`

**Service dependencies**:

- PGDG repository and signing key → PostgreSQL packages → PostgreSQL service.
- PostgreSQL service → PostgreSQL role `testuser` → database `testdb` → database privileges.
- PostgreSQL service and database → application database connectivity and Alembic migrations.
- Group `appuser` → user `appuser` → application directory `/opt/test-app`.
- Git checkout → virtual environment creation.
- Git checkout and virtual environment → requirements installation.
- Git checkout change → Alembic migration when `/opt/test-app/migrations/env.py` exists.
- Unit-file change → `systemctl daemon-reload`.
- Unit file and daemon reload → `test-app` enabled and running.
- `.env`, requirements, checkout, and migration-related changes → restart `test-app` where required to preserve Puppet notification behavior.
- Production Pushgateway package and health-check script → `push_app_metrics` cron job.

## Puppet Facts Used

- `fact('environment')`
  - Used by `profile::app::stack` to populate `environment_name`.
  - The value is not used after assignment.
  - Ansible equivalent: no direct equivalent required for this unused parameter.

- `$facts['environment']`
  - Used by `profile_app_stack::monitoring`.
  - Determines whether production-only Prometheus resources are realized.
  - Ansible equivalent: production inventory group membership, such as `'production' in group_names`.

- `$facts['os']['family']`
  - Used by the APT module to reject non-Debian-family systems.
  - Ansible equivalent: `ansible_facts.os_family`.

- `$facts['os']['name']`
  - Used by the APT module to install `gnupg` on Debian or Ubuntu.
  - Ansible equivalent: `ansible_facts.distribution`.

- `$facts['os']['release']['full']`
  - Used by optional APT PPA logic to select behavior by OS release.
  - Ansible equivalent: `ansible_facts.distribution_version`.

- `$facts['apt_update_last_success']`
  - Used by APT update-frequency logic to determine whether an APT index refresh is due.
  - Ansible equivalent: use a controlled `apt` task with `update_cache: true` and an approved `cache_valid_time`; do not recreate the custom timestamp fact unless exact behavior is required.

- `$facts['apt_sources']`
  - Used by optional APT PPA logic to detect existing source files.
  - Ansible equivalent: use idempotent repository modules and managed-file state.

## Template Conversion Notes

- `profile_app_stack/logrotate.conf.erb`
  - Destination: `/etc/logrotate.d/test-app`
  - Render count: `1`
  - Variables: `app_name`, `log_dir`, `log_max_size`, `log_rotate_count`
  - Effective values: `test-app`, `/var/log/test-app`, `100M`, `7`
  - Template source was not supplied.
  - Convert to `templates/logrotate.conf.j2` only after verifying rotation target paths, schedule, compression, missing-file handling, ownership/create directives, and postrotate logic.

- `profile_app_stack/app.env.erb`
  - Destination: `/opt/test-app/.env`
  - Render count: `1`
  - Variables: `app_name`, `app_port`, `db_url`, `secret_key`, `log_level`, `log_dir`, `worker_count`, `db_host`
  - Effective non-secret values: `test-app`, `8000`, `info`, `/var/log/test-app`, `2`, `localhost`
  - Secret values: derived database URL and application secret key
  - Ruby logic blocks: `1`
  - Inspect the source to preserve conditional line emission, quoting, escaping, and default behavior.
  - Render with mode `0600`, use `no_log: true`, and source both secrets from Ansible Vault.

- `profile_app_stack/app.service.epp`
  - Destination: `/etc/systemd/system/test-app.service`
  - Render count: `1`
  - Variables: `app_name`, `app_dir`, `app_user`, `app_group`, `app_port`, `worker_count`, `worker_class`, `max_requests`, `graceful_timeout`, `log_dir`, `log_level`
  - Effective values: `test-app`, `/opt/test-app`, `appuser`, `appuser`, `8000`, `2`, `sync`, `1000`, `30`, `/var/log/test-app`, `info`
  - EPP logic blocks: `1`
  - Inspect the source before conversion, particularly `ExecStart`, environment-file use, logging options, restart policy, conditional directives, and assembled command arguments.
  - Notify the systemd daemon-reload handler on unit changes.

## PuppetDB Dependencies

**Context**: This module does not use PuppetDB for cross-node discovery or queries. The APT module contains local catalog resource collectors that must be preserved as ordering and state-management behavior during migration.

- **Resource Collectors** (`<<| |>>`):
  - `Apt::Key <| title == $title |>` in `migration-dependencies/apt/manifests/key.pp`.
  - This collector selects matching `Apt::Key` resources in the local Puppet catalog by title.
  - It is not a PuppetDB cross-node query and does not require a centralized infrastructure-data replacement.
  - Migration note: inspect all attributes applied by the collector and preserve its key-resource ordering, refresh, subscription, and state-management effects using explicit Ansible tasks and handlers.

- **Virtual Resources**:
  - `profile_app_stack::monitoring` declares local virtual package, service, and cron resources and realizes them only when `environment=production`.
  - Migration note: implement these as explicit Ansible tasks conditioned on production inventory membership; no PuppetDB resource collection is required.

- **Exported Resources**:
  - No exported (`@@`) resources.

- **PuppetDB Queries**:
  - No `puppetdb_query()` calls.

- **Host Identity Data**:
  - No PuppetDB host identity or cross-node classification data is consumed.

## Checks for the Migration

**Files to verify**:

- `/var/log/test-app`
  - Exists as a directory.
  - Owner/group: `appuser:appuser`.
  - Mode: `0755`.

- `/etc/logrotate.d/test-app`
  - Owner/group: `root:root`.
  - Mode: `0644`.
  - Validate with `logrotate -d /etc/logrotate.d/test-app`.

- `/opt/test-app`
  - Exists as a Git checkout.
  - Source: `file:///tmp/test-app-repo`.
  - Revision: `master`.
  - Owner/group: `appuser:appuser`.

- `/opt/test-app/venv/bin/activate`
  - Exists after virtualenv creation.

- `/opt/test-app/.env`
  - Owner/group: `appuser:appuser`.
  - Mode: `0600`.
  - Do not display content in CI output, shell history, debug output, or Ansible logs.

- `/usr/local/bin/db-backup.sh`
  - Owner/group: `root:appuser`.
  - Mode: `0750`.
  - Validate shell syntax and perform a non-destructive backup test after confirming script behavior.

- `/usr/local/bin/app-healthcheck.sh`
  - Owner/group: `root:root`.
  - Mode: `0755`.
  - Validate HTTP health-check behavior and, on production nodes, metrics-push behavior.

- `/etc/systemd/system/test-app.service`
  - Owner/group: `root:root`.
  - Mode: `0644`.
  - Validate with `systemd-analyze verify /etc/systemd/system/test-app.service`.

**Service endpoints to check**:

- **PostgreSQL testdb**: `localhost:5432`
  - Verify PostgreSQL is listening on TCP port `5432`.
  - Verify database `testdb` exists.
  - Verify role `testuser` exists.
  - Verify `testuser` owns `testdb`.
  - Verify `testuser` has required database privileges.

- **test-app**: `http://localhost:8000/health`
  - Verify `test-app` is enabled and running.
  - Verify the health endpoint returns success.
  - Verify the root health-check cron executes every two minutes.

- **Prometheus monitoring**: production nodes only
  - Verify `prometheus-node-exporter` is installed, enabled, and running.
  - Verify `prometheus-pushgateway` is installed.
  - Verify `appuser` can execute `/usr/local/bin/app-healthcheck.sh --push-metrics`.
  - Verify the `push_app_metrics` cron job executes every five minutes as `appuser`.

**Templates rendered**:

- `profile_app_stack/logrotate.conf.erb` → `/etc/logrotate.d/test-app` — `1` render
- `profile_app_stack/app.env.erb` → `/opt/test-app/.env` — `1` render
- `profile_app_stack/app.service.epp` → `/etc/systemd/system/test-app.service` — `1` render

## Pre-flight checks:

```bash
# Resolve mandatory migration inputs before deployment.
# Verify the exact Python package value selected for app_stack_python_version.
# Verify the PostgreSQL 15 package array for the target distribution.
# Verify the PostgreSQL service unit name for the target distribution.
# Verify PGDG repository location, release, signing-key ID, and signing-key source.
# Locate profile_app_stack::app_db_url and preserve its exact URL format and escaping.
# Locate or reconstruct backup.sh, healthcheck.sh, logrotate.conf.erb, app.env.erb, and app.service.epp.
# Inspect apt::params and apt::key collector behavior before replacing APT key management.

# Confirm the managed host operating system is Debian-family if retaining the PGDG/APT implementation.
test -f /etc/debian_version

# Verify the local Git repository exists on every managed host.
test -d /tmp/test-app-repo/.git

# Verify the checked-out application supplies requirements and optional migration files.
test -f /opt/test-app/requirements.txt
test -f /opt/test-app/migrations/env.py || true

# Verify the selected Python interpreter supports virtual environments.
<python_version> -m venv --help

# PostgreSQL testdb instance checks.
systemctl status <postgresql_service_name>
sudo -u postgres psql -d postgres -c '\du'
sudo -u postgres psql -d postgres -c '\l'
sudo -u postgres psql -d testdb -c '\dp'

# test-app service checks.
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/test-app.service
systemctl enable --now test-app
systemctl status test-app
curl --fail http://localhost:8000/health

# File and template checks.
logrotate -d /etc/logrotate.d/test-app
test -x /usr/local/bin/db-backup.sh
test -x /usr/local/bin/app-healthcheck.sh

# Production-only Prometheus checks.
systemctl status prometheus-node-exporter
sudo -u appuser /usr/local/bin/app-healthcheck.sh --push-metrics

# Ensure app_stack_db_password and app_stack_secret_key are stored in Ansible Vault.
# Mark all credential-bearing environment, PostgreSQL user, database URL, migration,
# and template-rendering tasks with no_log: true.
```