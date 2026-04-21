## ADDED Requirements

### Requirement: Management console provides dedicated navigation to each admin page
The system SHALL provide a shared admin console shell with navigation links to dedicated pages for account management, platform configuration, notification management, execution history query, and system settings.

#### Scenario: Administrator opens a management page
- **WHEN** an authenticated administrator opens any admin management page
- **THEN** the page is rendered inside the shared admin console shell
- **THEN** the navigation shows links to account management, platform configuration, notification management, execution history query, and system settings

### Requirement: Navigation indicates the current page and remains usable on small screens
The system SHALL visually indicate the active navigation item for the current page and SHALL keep the navigation usable on mobile-width screens.

#### Scenario: Administrator switches between admin pages
- **WHEN** an authenticated administrator visits one of the dedicated admin pages
- **THEN** the matching navigation item is highlighted as active
- **THEN** the navigation remains accessible without horizontal page breakage on narrow screens
