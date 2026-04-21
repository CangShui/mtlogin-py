## MODIFIED Requirements

### Requirement: System manages login accounts as independent records
The system SHALL provide a dedicated login account management page where administrators can create, edit, enable, disable, and view multiple login accounts independently.

#### Scenario: Administrator creates a new login account
- **WHEN** an administrator submits a valid login account form on the account management page
- **THEN** the system creates a distinct account record
- **THEN** the account list shows the account name or username, bound platform, and enabled state

## ADDED Requirements

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
