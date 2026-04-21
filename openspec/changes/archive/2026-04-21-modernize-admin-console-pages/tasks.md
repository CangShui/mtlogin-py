## 1. Shared Admin Shell And Routing

- [x] 1.1 Extract the current single-page admin template into a shared layout with modernized navigation, header, flash messaging, and responsive styling tokens.
- [x] 1.2 Add dedicated GET routes for account management, platform configuration, notification management, execution history query, and system settings, and redirect the legacy `/dashboard` entry to the default page.
- [x] 1.3 Update POST action redirects so save, toggle, and run operations return to the correct dedicated page instead of the legacy single dashboard view.

## 2. Page Split For Existing Capabilities

- [x] 2.1 Create separate templates for platform configuration, notification management, account management, execution history query, and system settings using the shared admin shell.
- [x] 2.2 Move the existing administrator credential form out of the mixed dashboard content and into the dedicated system settings page.
- [x] 2.3 Preserve current platform, notification, account, and history management behaviors while removing unrelated panels from each page.

## 3. Account List Operational Fields

- [x] 3.1 Extend the account list query/context to include latest uploaded amount, downloaded amount, bonus, and last successful login time from the most recent execution record.
- [x] 3.2 Compute and expose each account's next scheduled execution time from its cron expression, with explicit empty-state handling for missing or invalid schedules.
- [x] 3.3 Update the account management table layout to display the new operational columns in a readable desktop and mobile-friendly format.

## 4. Verification And Documentation

- [x] 4.1 Verify each dedicated page can be opened, navigated, and submitted successfully with flash messages and correct active navigation state.
- [x] 4.2 Verify the account list shows the new execution summary fields and next-run values for accounts with and without execution history.
- [x] 4.3 Update README and admin usage documentation to describe the new multi-page console structure and page entry points.
