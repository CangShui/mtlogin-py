## 1. Frontend Scaffold And Template Migration

- [x] 1.1 Create a new `frontend/` Vue admin project in this repository using `/Users/haojiayu/Documents/me/github/v3-admin-vite-main` as the structural baseline.
- [x] 1.2 Keep the imported frontend scaffold aligned with the template project's dependency versions, including `vite 7.3.1`, and remove unrelated demo, permission, and example modules not needed by MTLogin.
- [x] 1.3 Configure frontend routing, layout, and shared state for login, account management, platform configuration, notification management, execution history, and system settings pages.

## 2. Backend API Surface

- [x] 2.1 Add authenticated `/api/admin/**` JSON endpoints for session login/logout/status and for reading management page bootstrap data.
- [x] 2.2 Add JSON mutation endpoints for platform toggles, notification save/toggle, account save/toggle/run, and administrator settings updates by reusing existing validation and persistence rules.
- [x] 2.3 Ensure unauthenticated API requests return SPA-friendly authentication errors instead of HTML redirects.

## 3. SPA Delivery And Integration

- [x] 3.1 Implement Vue pages that consume the new admin APIs for account, platform, notification, history, and system settings workflows.
- [x] 3.2 Configure Vite development proxy and production build output so Flask can serve the built SPA and preserve deep-link route refresh behavior.
- [x] 3.3 Migrate the admin login flow to the Vue frontend while keeping Flask session authentication as the source of truth.

## 4. Verification And Rollout

- [x] 4.1 Verify in development that the Vue app can log in, navigate between admin routes without full page reload, and complete all core management operations.
- [x] 4.2 Verify production-style build integration, including Flask static asset delivery, SPA route fallback, and authenticated API behavior after refresh.
- [x] 4.3 Update README and developer setup documentation for the new frontend toolchain, build commands, and deployment flow.
