# MIGRATION FAILED for profile_app_stack

**Failure Reason:** Molecule generation/validation failed: Deployment playbook does not include x2a.project.profile_app_stack: ansible/run_profile_app_stack.yml

## Migration Summary

- **Total items:** 47
- **Completed:** 37
- **Pending:** 10
- **Missing:** 0
- **Errors:** 0
- **Write attempts:** 1
- **Validation attempts:** 0

## Partial Validation Report

_Not run_

### Review Report

## Review Summary

### Findings
- [Missing Prerequisites] High: `tasks/database.yml`:Install PostgreSQL signing key - `/etc/apt/keyrings` was assumed to exist before downloading the PGDG signing key. **Fixed** by creating the directory with root ownership and `0755` mode immediately before the key download.
- [Missing Package Dependency] Medium: `tasks/python.yml`:Render application logrotate configuration - The role rendered a file owned by the `logrotate` application without ensuring that application was installed. **Fixed** by adding `logrotate` to the runtime package installation.
- [Missing Package Dependency] Medium: `tasks/app.yml`:Install application health-check script - The health-check script invokes `curl`, but `curl` was not ensured outside the local-PostgreSQL-only path. **Fixed** by adding `curl` to the general runtime package installation.
- [Missing Package Dependency] High: `tasks/database.yml`:Install database backup script - The backup script invokes `pg_dump`, but a PostgreSQL client was only installed for local database provisioning. Remote-database deployments would install and schedule a broken script. **Fixed** by ensuring `postgresql-client` is installed unconditionally.
- [Idempotency] High: `tasks/database.yml`:Create application PostgreSQL database - `createdb` was executed on every local deployment and relied on an exit-code workaround when the database already existed. **Fixed** by checking for database existence first and running `createdb` only when absent.
- [Idempotency] Medium: `tasks/database.yml`:Create application PostgreSQL role - The password-setting role command necessarily updates the role each run but did not accurately report that behavior. **Fixed** by declaring `changed_when: false`; the SQL remains safe to re-run.
- [Ordering] Medium: `tasks/app.yml`:Check out application repository - A changed checkout did not notify the application restart handler. This could leave a running service using prior application code when requirements and environment were unchanged. **Fixed** by notifying `Restart application` from the Git checkout task.
- [Runtime Correctness] High: `templates/app.service.j2` - The generated systemd service declared `Type=notify`, while its Gunicorn `ExecStart` command does not enable systemd notification support. Systemd can wait for a notification that never arrives and fail startup. **Fixed** by using `Type=simple`.
- [Runtime Correctness] Medium: `files/app-healthcheck.sh` and `tasks/monitoring.yml` - The health-check script wrote to hard-coded `/var/log/myapp-api`, which does not match configurable `app_stack_log_dir` and may not exist. **Fixed** by making the script honor `LOG_DIR` and passing the configured directory in both cron jobs.
- [Runtime Correctness] Medium: `files/db-backup.sh` - The root-owned cron job ran `sudo -u postgres`, requiring `sudo` to be installed despite it not being a role dependency. **Fixed** by invoking `pg_dump` directly as the cron’s root user.

### Changes Made
- `tasks/python.yml`: Added `curl` and `logrotate` to the package prerequisites.
- `tasks/database.yml`: Created `/etc/apt/keyrings`; ensured the PostgreSQL client is installed for backups; made database creation explicitly idempotent; normalized role-provisioning change reporting.
- `tasks/app.yml`: Added a service-restart notification to repository checkout changes.
- `tasks/monitoring.yml`: Passed the configured application log directory to health-check cron executions.
- `templates/app.service.j2`: Changed systemd service type from `notify` to `simple`.
- `files/app-healthcheck.sh`: Made health-check logging use configurable `LOG_DIR`.
- `files/db-backup.sh`: Removed the undeclared `sudo` runtime dependency.

### No Issues Found
- [Invalid Module Parameters] No unsupported module parameters were found.
- [Missing Argument Specs] `meta/argument_specs.yml` exists and covers the defaults and required AAP credential variables.
- [Missing User/Group Prerequisites] The application group and user are created before being used for ownership or execution.
- [Service Ordering] PostgreSQL and Prometheus services are installed before enablement/start, and the application unit is rendered and daemon-reloaded before the application service is enabled and started.

### Molecule Test Generation

**Status:** generation_failed_unverified

Static generation/validation failed: Deployment playbook does not include x2a.project.profile_app_stack: ansible/run_profile_app_stack.yml

### Partial Checklist

## Checklist: profile_app_stack

### Templates
- [x] profile_app_stack/logrotate.conf.erb → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/templates/logrotate.conf.j2 (complete) - Converted verified ERB logrotate template to Jinja2.
- [x] profile_app_stack/app.env.erb → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/templates/app.env.j2 (complete) - Converted verified ERB environment template; production conditional is inventory-group based.
- [x] profile_app_stack/app.service.epp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/templates/app.service.j2 (complete) - Converted verified EPP systemd unit to Jinja2, preserving the computed stop timeout.

### Recipes → Tasks
- [x] site-modules/profile_app_stack/manifests/init.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/main.yml (complete) - Migrated ordered phase orchestration and generated in-memory encoded PostgreSQL URL from AAP credentials.
- [x] site-modules/profile_app_stack/manifests/python.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/python.yml (complete) - Migrated Python dependency, account, log directory, and logrotate resources.
- [x] site-modules/profile_app_stack/manifests/database.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Migrated local PostgreSQL provisioning, backup script, and scheduled backup.
- [x] site-modules/profile_app_stack/manifests/app.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/app.yml (complete) - Migrated deployment, virtualenv, requirements, secret environment, health-check script, and conditional Alembic migrations.
- [x] site-modules/profile_app_stack/manifests/service.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/service.yml (complete) - Migrated systemd unit rendering, handler flush for daemon reload ordering, and service enablement.
- [x] site-modules/profile_app_stack/manifests/monitoring.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/monitoring.yml (complete) - Migrated production-group-gated Prometheus resources and universal health-check cron.
- [x] site-modules/profile_postgresql/manifests/init.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Integrated repository, installation, and service ordering into the consolidated database task file.
- [x] site-modules/profile_postgresql/manifests/repo.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Integrated PGDG signing key and repository configuration into the consolidated database task file.
- [x] site-modules/profile_postgresql/manifests/install.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Integrated PostgreSQL server, client, libpq, and psycopg2 package installation into database tasks.
- [x] site-modules/profile_postgresql/manifests/service.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Integrated PostgreSQL service enablement and startup into database tasks.
- [x] site-modules/role/manifests/app_server.pp → ansible/run_profile_app_stack.yml (complete) - Created app-server entry playbook for the migrated application-stack role; sibling base, HAProxy, and Redis profiles are separate migrations.
- [x] site-modules/profile/manifests/app/stack.pp → ansible/run_profile_app_stack.yml (complete) - Integrated thin profile wrapper into the application-stack entry playbook.
- [x] migration-dependencies/apt/manifests/init.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Integrated Debian validation, repository prerequisites, PGDG configuration, and controlled package index refresh into database tasks.
- [x] migration-dependencies/apt/manifests/params.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Retained applicable Debian APT path and key-management defaults through explicit PGDG repository tasks; unused proxy and purge settings are not configured.
- [x] migration-dependencies/apt/manifests/update.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Replaced timestamp-fact refresh behavior with bounded apt cache refresh in database prerequisites.
- [x] migration-dependencies/apt/manifests/conf.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - No configured custom APT conf resources were supplied; PGDG-specific requirements are directly managed in database tasks.
- [x] migration-dependencies/apt/manifests/setting.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - No supplied APT settings require conversion; repository configuration is managed declaratively with apt_repository.
- [x] migration-dependencies/apt/manifests/source.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Replaced the configured PGDG Apt source with a signed apt_repository resource.
- [x] migration-dependencies/apt/manifests/key.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Replaced deprecated apt-key handling and collector ordering with a signed keyring downloaded before repository creation.
- [x] migration-dependencies/apt/manifests/keyring.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - Migrated relevant PGDG keyring behavior using get_url into /etc/apt/keyrings with root ownership.
- [x] migration-dependencies/apt/manifests/pin.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - No configured Apt pin resources were supplied, so no pin preferences are managed.
- [x] migration-dependencies/apt/manifests/ppa.pp → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/database.yml (complete) - No PPA resources were supplied; no Ubuntu PPA is configured.

### Attributes → Variables
- [x] site-modules/profile_app_stack/data/common.yaml → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/defaults/main.yml (complete) - Migrated effective application defaults and module log rotation fallback values; secrets are sourced from AAP credentials.
- [x] site-modules/profile_app_stack/data/environment/production.yaml → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/vars/production.yml (complete) - Migrated non-secret legacy production overrides; encrypted secret key is supplied by AAP credentials.
- [x] site-modules/profile_app_stack/data/environment/staging.yaml → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/vars/staging.yml (complete) - Migrated non-secret legacy staging overrides; plaintext secret key is replaced by the AAP credential variable.

### Static Files
- [x] puppet:///modules/profile_app_stack/backup.sh → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/files/db-backup.sh (complete) - Copied supplied Puppet module static backup script.
- [x] puppet:///modules/profile_app_stack/healthcheck.sh → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/files/app-healthcheck.sh (complete) - Copied supplied Puppet module static health-check script.

### Structure Files
- [x] N/A → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/meta/main.yml (complete) - Created standard meta/main.yml
- [x] N/A → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/handlers/main.yml (complete) - Created systemd reload and application restart handlers.
- [x] data/common.yaml → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/defaults/main.yml (complete) - Migrated effective control-repository values and added PostgreSQL service default; secret values are supplied through AAP credentials.
- [x] defaults/main.yml → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/meta/argument_specs.yml (complete) - Generated argument specifications for role defaults and required AAP credential variables.

### Molecule Testing
- [ ] N/A → ansible/run_profile_app_stack.yml (pending)
- [ ] N/A → ansible/molecule/requirements.yml (pending)
- [ ] N/A → ansible/molecule/README.md (pending)
- [ ] N/A → ansible/molecule/profile_app_stack/molecule.yml (pending)
- [ ] N/A → ansible/molecule/profile_app_stack/inventory/hosts.yml (pending)
- [ ] N/A → ansible/molecule/profile_app_stack/create.yml (pending)
- [ ] N/A → ansible/molecule/profile_app_stack/destroy.yml (pending)
- [ ] N/A → ansible/molecule/profile_app_stack/prepare.yml (pending)
- [ ] N/A → ansible/molecule/profile_app_stack/converge.yml (pending)
- [ ] N/A → ansible/molecule/profile_app_stack/verify.yml (pending)

### Credentials → AAP Configuration
- [x] N/A → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/aap-configuration/controller_credential_types.yml (complete)
- [x] N/A → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/aap-configuration/controller_credentials.yml (complete)
- [x] N/A → ansible/collections/ansible_collections/x2a/project/roles/profile_app_stack/tasks/validate_credentials.yml (complete)


## Telemetry

```
Phase: migrate
Duration: 0.00s

Agent Metrics:
  AAP Collection Discovery: 25.04s
    Tokens: 46130 in, 670 out
    Tools: aap_get_collection_detail: 1, aap_list_collections: 1
    collections_found: 1
  Credential Extractor: 9.55s
    Tokens: 14722 in, 748 out
    credentials_found: 2
  Export Planner: 64.93s
    Tokens: 113628 in, 5142 out
    Tools: add_checklist_task: 34, get_checklist_summary: 1, list_checklist_tasks: 1, list_directory: 1, read_file: 1
  Ansible Role Writer: 283.60s
    Tokens: 2658368 in, 13997 out
    Tools: ansible_lint: 1, ansible_write: 14, copy_file: 2, file_search: 4, get_checklist_summary: 1, list_checklist_tasks: 1, read_file: 29, update_checklist_task: 33, write_file: 3
    attempts: 1
    complete: True
    files_created: 37
    files_total: 47
  ReviewAgent: 240.97s
    Tokens: 184784 in, 19138 out
    Tools: ansible_write: 5, get_checklist_summary: 1, list_directory: 5, read_file: 26, write_file: 3
  Molecule Test Generator: 0.02s
```