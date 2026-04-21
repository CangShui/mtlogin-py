## MODIFIED Requirements

### Requirement: Management console provides dedicated navigation to each admin page
The system SHALL provide a shared admin console shell with navigation links to dedicated frontend routes for account management, platform configuration, notification management, execution history query, and system settings.

#### Scenario: Administrator opens a management page
- **WHEN** an authenticated administrator opens any admin management route in the frontend console
- **THEN** the page is rendered inside the shared admin console shell
- **THEN** the navigation shows links to account management, platform configuration, notification management, execution history query, and system settings

### Requirement: Navigation indicates the current page and remains usable on small screens
The system SHALL visually indicate the active navigation item for the current frontend route and SHALL keep the navigation usable on mobile-width screens.

#### Scenario: Administrator switches between admin pages
- **WHEN** an authenticated administrator visits one of the dedicated admin frontend routes
- **THEN** the matching navigation item is highlighted as active
- **THEN** the navigation remains accessible without horizontal page breakage on narrow screens

## ADDED Requirements

### Requirement: Management navigation supports route-driven page switching without full document reload
The system SHALL allow administrators to switch between management sections through frontend routing so that page changes do not require a full document reload for normal in-app navigation.

#### Scenario: Administrator changes sections from the sidebar
- **WHEN** an authenticated administrator selects another management section from the console navigation
- **THEN** the frontend updates to the target management route
- **THEN** the target page is displayed within the same management application shell
