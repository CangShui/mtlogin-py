# login-account-management Specification

## Purpose
TBD - created by archiving change add-platform-notification-and-history. Update Purpose after archive.
## Requirements
### Requirement: System manages login accounts as independent records
The system SHALL provide a dedicated login account management page where administrators can create, edit, enable, disable, and view multiple login accounts independently.

#### Scenario: Administrator creates a new login account
- **WHEN** an administrator submits a valid login account form on the account management page
- **THEN** the system creates a distinct account record
- **THEN** the account list shows the account name or username, bound platform, and enabled state

### Requirement: Each account binds exactly one enabled platform
The system SHALL require every login account to bind to exactly one enabled platform entry before the account can be saved.

#### Scenario: Account is saved with a platform selection
- **WHEN** an administrator creates or edits an account and selects one enabled platform
- **THEN** the system saves the account with that platform binding

### Requirement: Accounts can bind multiple notification channels
The system SHALL allow administrators to select zero or more enabled notification channels for each login account.

#### Scenario: Account binds more than one notification channel
- **WHEN** an administrator checks multiple enabled notification channels in the account form
- **THEN** the system saves all selected channel bindings for that account

### Requirement: Account execution fields preserve existing secrets when blank
The system SHALL keep the current saved value for account secret fields when an administrator edits an account and leaves those secret inputs blank.

#### Scenario: Password and token remain unchanged after blank edit
- **WHEN** an administrator edits an existing account and leaves password, TOTP, or auth token inputs blank
- **THEN** the system preserves the previously stored secret values for those fields

### Requirement: Account configuration includes current task execution options
The system SHALL support the existing task execution fields for each account, including username, password, TOTP secret, proxy, cron expression, auth token, DID, timeout, cookie mode, and skip-cache behavior.

#### Scenario: Administrator configures scheduled execution for an account
- **WHEN** an administrator saves an account with login credentials and a valid cron expression
- **THEN** the system persists the account-specific execution options for future scheduled runs

### Requirement: Account list shows latest execution summary and next scheduled time
The system SHALL show the latest available execution summary for each account in the account management list, including uploaded amount, downloaded amount, bonus, last successful login time, and next scheduled execution time.

#### Scenario: Account has execution history and valid schedule
- **WHEN** an administrator opens the account management page for an account that has execution history and a valid cron schedule
- **THEN** the account row shows the latest uploaded amount, downloaded amount, and bonus values from the most recent execution record
- **THEN** the account row shows the latest successful login time returned by execution history
- **THEN** the account row shows the next scheduled execution time calculated from the account cron expression

#### Scenario: Account has no execution history or no next run
- **WHEN** an administrator opens the account management page for an account that has no execution history, no cron expression, or an invalid cron expression
- **THEN** the account row shows explicit empty-state values for the missing execution summary fields
- **THEN** the account row shows no next scheduled execution time until a valid schedule is available

