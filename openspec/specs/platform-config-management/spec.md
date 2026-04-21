# platform-config-management Specification

## Purpose
TBD - created by archiving change add-platform-notification-and-history. Update Purpose after archive.
## Requirements
### Requirement: System provides a platform configuration list
The system SHALL provide a dedicated platform configuration page that administrators can open from the management console, and the list SHALL contain a built-in `mt` platform entry.

#### Scenario: Built-in mt platform is available
- **WHEN** an administrator opens the platform configuration page after the upgrade
- **THEN** the system shows a platform row for `mt`
- **THEN** the `mt` row is marked as enabled by default

### Requirement: Built-in mt platform uses fixed API endpoint settings
The system SHALL treat `mt` as a built-in platform whose `API Host` and `API Referer` are fixed values and SHALL display those values as read-only in the management UI.

#### Scenario: Administrator inspects mt platform details
- **WHEN** an administrator views or edits the built-in `mt` platform
- **THEN** the system shows `api.m-team.io` as `API Host`
- **THEN** the system shows `https://kp.m-team.cc/` as `API Referer`
- **THEN** the administrator cannot modify those two fields

### Requirement: Only enabled platforms can be assigned to accounts
The system SHALL only allow enabled platform entries to appear as selectable options when administrators create or edit login accounts.

#### Scenario: Disabled platform is excluded from account form
- **WHEN** an administrator opens the account creation or edit form
- **THEN** the platform selector only contains enabled platform entries

