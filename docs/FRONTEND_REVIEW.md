# Frontend update review — September 10, 2026

The existing React workspace and Django API were continued and verified together. This update improves product browsing, exports, image handling and shop selection. Existing unfinished changes were already present throughout the repository when this work started; the login, dashboard, CRUD pages and account workflows were retained and tested, rather than claimed as new work in this update.

## What changed

| Area | Update | Main files |
| --- | --- | --- |
| Product browsing | Added sorting by newest, name, price and stock. Sorting runs in Django before pagination, with stable ID tie breakers in the UI. | `frontend/src/pages/ResourcePage.jsx`, `product/views/product_view.py` |
| Product export | Added Export products, including every page matching the current search, shop, status and low-stock filters. CSV values are quoted, embedded quotes escaped and formula-like text protected. | `frontend/src/api.js`, `frontend/src/pages/ResourcePage.jsx` |
| Shop selection | Shop changes clear dependent brand/category filters. Filter choices narrow to that shop. Shop labels distinguish identically named categories and brands in admin choices. | `frontend/src/pages/ResourcePage.jsx` |
| Catalog controls | Added Refresh, clearer record-list guidance, correct Categories wording and an accessible pressed state for the low-stock toggle. | `frontend/src/pages/ResourcePage.jsx`, `frontend/src/styles.css` |
| Images | Added local image previews before submission, existing-image previews when editing and field-level API upload errors. Preview URLs are released when replaced or closed. | `frontend/src/api.js`, `frontend/src/pages/ResourcePage.jsx` |
| Role requests | Prevented the create URL shortcut from opening a request form for administrators or members without a shop. | `frontend/src/pages/ResourcePage.jsx` |
| Guidance and repository | Added export help and startup instructions. Ignored frontend dependencies, build output and temporary test artifacts. | `frontend/src/pages/Help.jsx`, `README.md`, `.gitignore` |
| Tests | Replaced a corrupt PNG fixture with a valid image; added invalid-image feedback, image removal, sorting, export, filter reset, recovery and mobile checks. Added API sorting/pagination/isolation tests. | `frontend/tests/workspace.spec.js`, `common/tests.py` |

`frontend/src/components.jsx` also received formatting only.

## Backend integration

The built frontend is served by Django at `/`; it calls `/api/v1/` using the existing token-authenticated API. Uploaded images load through `/media/`. Development through Vite uses its existing API/media proxy. No mocked catalog data is used by the application.

The browser suite exercised real login/logout, dashboard reads, category/brand/product-line/product creation, image upload/removal, stock updates, password-confirmed deletion, shops/roles/users, ban/unban, role-request approval/submission and password changes. Destructive test operations ran only against disposable synthetic data.

The configured database has no pending migrations. No schema changes or real-account password changes were needed for this update.

## Validation results

- Production frontend build: passed.
- Backend suite: 23 tests passed using isolated SQLite settings.
- Full Chrome browser suite: 7 tests passed against a temporary Django database.
- Additional mobile rerun: passed for dashboard navigation and the new product toolbar at 390 px width, with no page-level horizontal overflow.
- Prettier formatting check: passed; the final screenshot-test edit was formatted afterward.
- Django system check: passed.
- Migration drift check: no changes detected.
- Configured database migration plan: no planned operations.
- Local application at `http://127.0.0.1:8000/`: HTTP 200.

The original browser run failed because its PNG fixture was corrupt. Django correctly rejected it; image validation was preserved. Windows sandbox restrictions also blocked test-server cleanup; the completed browser runs used permission to manage their own temporary server processes.

## Review the application

Open **http://127.0.0.1:8000/** and use your existing account. This server uses your configured database, so changes you make there are real shop changes.

1. Open Products and try each sort option.
2. Combine search, shop and status filters; switch shops and confirm categories/brands reset.
3. Toggle Low stock, export products and compare the CSV with the filtered results.
4. Add or edit a product, choose a valid image and inspect its preview before saving.
5. Try the mobile layout and navigation.

Screenshots use synthetic test records:

- [Desktop product catalog](screenshots/products.png)
- [Mobile product catalog](screenshots/mobile-products.png)
- [Mobile dashboard](screenshots/mobile.png)
- [Desktop dashboard](screenshots/dashboard.png)
- [Login](screenshots/login.png)

The review is local; no deployment or Git commit was performed. Production hosting, HTTPS and production media/static serving remain deployment setup. Large exports fetch pages sequentially and do not represent an atomic snapshot if another user changes the catalog during export. Browser mutation flows were tested on SQLite; a PostgreSQL-specific suite was not run in this update.
