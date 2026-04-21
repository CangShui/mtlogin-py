## ADDED Requirements

### Requirement: Management console is delivered as a Vite-built Vue single-page application
The system SHALL deliver the administrator management console as a Vue 3 single-page application built with the template project's Vite-based toolchain, with `vite 7.3.1` as the initial build baseline, rather than relying on Flask-rendered management templates as the primary UI.

#### Scenario: Administrator opens the management console in production
- **WHEN** an authenticated administrator opens the management console after the frontend migration
- **THEN** the system serves the built Vue application shell for the admin UI
- **THEN** the administrator can access the management console without relying on server-rendered management templates as the primary page content

### Requirement: Frontend routes support direct refresh and deep-link access
The system SHALL support direct browser access and refresh for admin frontend routes by returning the SPA entry document for managed frontend paths while keeping backend API paths distinct.

#### Scenario: Administrator refreshes a frontend route
- **WHEN** an authenticated administrator directly opens or refreshes an admin frontend route such as the account management page
- **THEN** the system returns the SPA entry document for that route
- **THEN** the frontend application restores the corresponding management page after load
