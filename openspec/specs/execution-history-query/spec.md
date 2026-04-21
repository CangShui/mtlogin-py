# execution-history-query Specification

## Purpose
TBD - created by archiving change add-platform-notification-and-history. Update Purpose after archive.
## Requirements
### Requirement: System stores an execution record for every account run
The system SHALL create a persistent execution record every time a login account is executed manually or by schedule.

#### Scenario: Scheduled account execution writes history
- **WHEN** the scheduler runs an enabled account
- **THEN** the system stores a history record containing the account, platform, trigger mode, start time, finish time, status, and result message

### Requirement: Execution records include key run metrics
The system SHALL store the key execution metrics returned by the login job, including username, uploaded amount, downloaded amount, bonus, last login time, and last browse time, when those values are available.

#### Scenario: Successful run captures metrics
- **WHEN** an account run finishes successfully with status details from the platform
- **THEN** the corresponding execution record includes the returned metric fields

### Requirement: Administrators can query execution history with filters
The system SHALL provide a dedicated execution history query page that supports filtering by account, platform, execution status, and time range.

#### Scenario: Administrator filters execution history
- **WHEN** an administrator submits query filters for a specific account and a time range on the execution history page
- **THEN** the system returns only matching execution records

### Requirement: Execution history is ordered by newest runs first
The system SHALL show execution records in descending start-time order so that the most recent runs appear first.

#### Scenario: Administrator opens history without filters
- **WHEN** an administrator opens the execution history view with no filters
- **THEN** the newest execution records are displayed before older ones

