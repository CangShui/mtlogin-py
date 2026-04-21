## MODIFIED Requirements

### Requirement: System provides a platform configuration list
The system SHALL provide a dedicated platform configuration page that administrators can open from the management console, and the list SHALL contain a built-in `mt` platform entry.

#### Scenario: Built-in mt platform is available
- **WHEN** an administrator opens the platform configuration page after the upgrade
- **THEN** the system shows a platform row for `mt`
- **THEN** the `mt` row is marked as enabled by default
