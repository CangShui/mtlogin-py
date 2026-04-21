# notification-channel-management Specification

## Purpose
TBD - created by archiving change add-platform-notification-and-history. Update Purpose after archive.
## Requirements
### Requirement: System manages notification channels as a list
The system SHALL provide a dedicated notification management page where administrators can create, edit, enable, disable, and view notification channel entries independently from login accounts.

#### Scenario: Administrator creates a tg notification channel
- **WHEN** an administrator submits a new notification channel from the notification management page with type `tg`
- **THEN** the system stores it as a distinct channel entry in the notification list
- **THEN** the notification list shows the channel name, type, and enabled state

### Requirement: Telegram channel fields match the current web configuration
For notification channels of type `tg`, the system SHALL collect and persist the Telegram bot token, Telegram chat ID, and Telegram proxy fields that are currently configured in the single-page task form.

#### Scenario: Administrator edits tg channel settings
- **WHEN** an administrator opens an existing `tg` channel for editing
- **THEN** the system shows the Telegram bot token as a masked secret field
- **THEN** the system shows the Telegram chat ID and Telegram proxy as editable values

### Requirement: Secret notification fields are preserved when left blank
The system SHALL preserve saved secret values for notification channels when an administrator submits an edit form with an empty secret field.

#### Scenario: Telegram token is not overwritten by a blank edit
- **WHEN** an administrator edits a `tg` channel and leaves the bot token field blank
- **THEN** the system keeps the previously saved bot token unchanged

### Requirement: Only enabled notification channels can be bound to accounts
The system SHALL only expose enabled notification channels as selectable options in the login account form.

#### Scenario: Disabled tg channel is hidden from account binding
- **WHEN** an administrator opens the account creation or edit form
- **THEN** disabled notification channels do not appear in the list of selectable bindings

