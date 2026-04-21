## MODIFIED Requirements

### Requirement: System manages notification channels as a list
The system SHALL provide a dedicated notification management page where administrators can create, edit, enable, disable, and view notification channel entries independently from login accounts.

#### Scenario: Administrator creates a tg notification channel
- **WHEN** an administrator submits a new notification channel from the notification management page with type `tg`
- **THEN** the system stores it as a distinct channel entry in the notification list
- **THEN** the notification list shows the channel name, type, and enabled state
