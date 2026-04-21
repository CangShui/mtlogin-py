## ADDED Requirements

### Requirement: System settings are managed on a dedicated page
The system SHALL provide a dedicated system settings page for system-level administration actions, separate from platform, notification, account, and execution history pages.

#### Scenario: Administrator opens system settings
- **WHEN** an authenticated administrator opens the system settings page
- **THEN** the page shows system-level configuration content without mixing platform, notification, account, or execution history forms on the same page

### Requirement: System settings page manages administrator credentials
The system SHALL allow administrators to update the administrator username and password from the dedicated system settings page by reusing the existing credential update rules.

#### Scenario: Administrator changes credentials from system settings
- **WHEN** an administrator submits valid updated administrator credentials on the system settings page
- **THEN** the system persists the new administrator credentials
- **THEN** the administrator can continue to access the management console with the updated credentials
