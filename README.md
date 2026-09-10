# Phone Shop Backend

Django REST API implementing the six Shop Owner and Super Admin use-case diagrams. The existing brand, category, tenant and product apps are retained; the accounts app supplies login, profiles, users, roles and role requests.

See [the diagram and source review](docs/DIAGRAM_REVIEW.md) for the image-by-image assessment, assumptions, corrected defects and test coverage.

## Frontend workspace

The React workspace is connected to the Django API for login, dashboard metrics, catalog management, shops, users, roles, role requests and profile settings. See [the frontend change review](docs/FRONTEND_REVIEW.md) for the September 10 update and a review checklist.

From `phone-shop-backend`, build the frontend and serve both UI and API together:

```powershell
cd ..\phone-shop-frontend
npm ci
npm run build
cd ..\phone-shop-backend
..\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/` and sign in with your existing email or phone number. The example uses the existing Windows virtual environment next to this repository; use your own activated Python environment on other systems.

For live frontend editing, leave Django running and run `npm run dev` in `../phone-shop-frontend`, then open `http://127.0.0.1:5173/`. Vite proxies `/api` and `/media` to Django on port 8000. An optional `API_PROXY_TARGET` in `../phone-shop-frontend/.env` changes that destination. Keep frontend requests relative so authentication and uploaded images use the same origin.

Product lists support `ordering` with `name`, `price`, `stock`, `created_at`, or `id`; prefix a field with `-` for descending order. For example, `products?ordering=price,id&low_stock=true`. The UI exports all products matching the current filters across every page.

To verify the built frontend with an isolated database:

```powershell
cd ..\phone-shop-frontend
npm run build
npm run test:e2e
npm run format:check
```

Browser tests require Google Chrome and use port 8011 with temporary SQLite data and uploads. They do not use the configured shop database. The standalone `tests/start-backend.py` script is a test fixture with test-only passwords and password hashing, not an application startup script.

## Setup

Tested with Python 3.14, Django 6.1.1 and Django REST Framework 3.18.1 using the supplied requirements.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configure your local `.env`. Keep your existing database credentials when upgrading:

```dotenv
SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=postgresql
DB_NAME=ps_db
DB_USER=postgres
DB_PASSWORD=your-database-password
DB_HOST=localhost
DB_PORT=5432
```

`DJANGO_DEBUG` takes precedence over `DEBUG`, avoiding unrelated system DEBUG values such as `release`. True/1/yes/on enable debug; other values disable it. PostgreSQL is the default database. For standalone SQLite development set `DB_ENGINE=sqlite`; PostgreSQL credentials are then unnecessary.

For an existing database, run the read-only audit before migrating:

```powershell
python manage.py check_shop_data
python manage.py migrate
```

For an empty database, run `migrate` first. Create a super admin with a unique email address, then start Django:

```powershell
python manage.py createsuperuser
python manage.py runserver
```

The API base is `http://127.0.0.1:8000/api/v1/`. API paths do not have trailing slashes. Django's admin remains at `/admin/`.

## Authentication and onboarding

Login accepts an exact username, a case-insensitive email address, or a phone number. Accounts made with `createsuperuser` can sign in using their username and chosen password. If multiple accounts share an email, use their distinct usernames; ambiguous identifiers are rejected.

Browser pages are guarded by `WorkspaceLoginRequiredMiddleware`. Signed-out requests, including direct links such as `/products`, redirect to `/login`. The login page and its static assets stay public. API login creates a server-side browser session tied to the issued token; logout, token revocation and banning invalidate page access. Existing Django admin sessions retain their normal page access and admin permission checks. API requests still require the Authorization token: the browser cookie alone cannot authorize API writes. Signed-out API navigation from a browser redirects to login; ordinary API clients receive HTTP 401. Hash routes are additionally guarded by the React authentication boundary because URL fragments are never sent to Django.

After upgrading, sign in once to establish the new browser session. No database migration is required. For deployment, serve private media through an authenticated endpoint or equivalent web-server access control; a public media server bypasses Django middleware.

1. Create the initial super admin using `createsuperuser`.
2. Log in by POSTing to `auth/login`:

```json
{"identifier": "admin@example.com", "password": "your-admin-password"}
```

The token is in `response.data.token`. Send it on subsequent API calls:

```http
Authorization: Token <token>
Content-Type: application/json
```

3. As the super admin, POST a shop to `tenants`:

```json
{"name": "My Phone Shop", "type": "PHONE", "status": "ACTIVE"}
```

4. POST a role to `roles`:

```json
{"name": "Shop Owner", "description": "Manage the assigned shop catalog", "can_manage_catalog": true}
```

5. POST an owner to `users`, using the IDs returned above:

```json
{
  "username": "shopowner",
  "email": "owner@example.com",
  "phone": "+85512345678",
  "password": "Choose-A-Strong-Unique-Password!",
  "tenant_id": 1,
  "role_id": 1
}
```

Users created through this API are ordinary users. A role never grants Django superuser or staff status. To assign an existing ordinary user to a shop and role, use `users/{id}/change-role` with `tenant_id`, `role_id`, and `admin_password`.

Owners log in using email or international-format phone number in `identifier`. Each account has one API token. Logout deletes it; password changes, bans, role changes and approved role requests also revoke it. Tokens do not expire automatically. The REST API accepts tokens; Django admin uses its own session login. Use HTTPS for production token traffic, as required by [DRF token authentication](https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication).

## Endpoints

Every path below is relative to `/api/v1/`.

| Path | Methods | Access / behavior |
| --- | --- | --- |
| `auth/login` | POST | Email/phone identifier + password; throttled to 10 requests/minute per client IP |
| `auth/logout` | POST | Authenticated; revoke token |
| `auth/profile` | GET, PUT, PATCH | Own username, email, phone; role/shop/privilege fields are read-only |
| `auth/change-password` | POST | `current_password`, `new_password`; log in again afterward |
| `tenants`, `tenants/{id}` | GET, POST / GET, PUT, PATCH, DELETE | Super admin |
| `brands`, `brands/{id}` | GET, POST / GET, PUT, PATCH, DELETE | Super admin or own-shop catalog role |
| `categories`, `categories/{id}` | GET, POST / GET, PUT, PATCH, DELETE | Super admin or own-shop catalog role |
| `product-lines`, `product-lines/{id}` | GET, POST / GET, PUT, PATCH, DELETE | Super admin or own-shop catalog role |
| `products`, `products/{id}` | GET, POST / GET, PUT, PATCH, DELETE | Super admin or own-shop catalog role |
| `roles`, `roles/{id}` | GET, POST / GET, PUT, PATCH, DELETE | Super admin role configuration |
| `available-roles` | GET | Authenticated; role choices for requests |
| `role-requests`, `role-requests/{id}` | GET, POST / GET | Owner submits/reads own requests; super admin reads all |
| `role-requests/{id}/approve` | POST | Super admin; assign requested role |
| `role-requests/{id}/reject` | POST | Super admin; keep existing role |
| `users`, `users/{id}` | GET, POST / GET, DELETE | Super admin |
| `users/{id}/change-role` | POST | `role_id`, optional `tenant_id`, required `admin_password` |
| `users/{id}/ban` | POST | Required `admin_password`; disable user and revoke token |
| `users/{id}/unban` | POST | Super admin; reactivate user |

For every super admin catalog/tenant/role DELETE, and for user deletion, role change and ban, provide the **acting admin's current password** in the JSON body:

```json
{"admin_password": "your-admin-password"}
```

Owners can delete their own unreferenced catalog records without that confirmation. Super admin accounts are protected from user-management mutations. Referenced brands/categories/product lines and assigned/requested roles return 400 on deletion; remove dependencies first.

## Search and filters

List endpoints paginate 50 records at a time. Use `page=2` for the next page. `search` performs case-insensitive text search.

| Resource | Search fields | Exact filters |
| --- | --- | --- |
| tenants | name | status (ACTIVE/INACTIVE), type |
| brands | name | tenant_id, status (ACTIVE/INACTIVE) |
| categories | name, slug, description | tenant_id |
| product-lines | name | tenant_id, category_id, brand_id |
| products | name, SKU, description | tenant_id, category_id, brand_id, status (AVAILABLE/UNAVAILABLE/ARCHIVED) |
| roles | name | — |
| users | username, email, phone | role_id, status (ACTIVE/BANNED) |
| role-requests | — | status (PENDING/APPROVED/REJECTED) |

An owner-supplied tenant filter never widens their shop access.

## Catalog request examples

POST `categories`:

```json
{"name": "Smartphones", "slug": "smartphones", "description": "Mobile phones"}
```

POST `brands`:

```json
{"name": "Apple", "description": "Phone brand", "status": "ACTIVE"}
```

Owners may omit the tenant; it is derived from their profile. Super admins must supply `tenant_id` for brand/category creation. Use the actual generated IDs in subsequent requests. Existing formats `BRA00001` and `CAT-0001` are preserved.

POST `product-lines`:

```json
{"name": "iPhone", "category_id": "CAT-0001", "brand_id": "BRA00001"}
```

POST `products`:

```json
{
  "name": "Example Phone",
  "sku": "PHONE-128-BLK",
  "category": "CAT-0001",
  "brand": "BRA00001",
  "product_line": 1,
  "description": "128 GB, black",
  "price": "499.00",
  "stock": 10,
  "status": "AVAILABLE"
}
```

The new product resource uses `tenant`, `category`, `brand`, and `product_line` as relationship input keys. A super admin must include `tenant`; an owner can omit it. `product_line` is optional. Filters consistently use `*_id` keys. Price is a nonnegative decimal and stock a nonnegative integer.

Use multipart form data for product `image` or brand `logo_url` uploads. Media is served by Django only with debug enabled; configure media hosting in deployment.

POST `role-requests` as an assigned user:

```json
{"role": 2, "reason": "Please change my catalog access"}
```

Approval/rejection endpoints accept an empty JSON body. Only one pending request is allowed per user.

## Responses

The original JSON envelope is retained:

```json
{
  "code": 200,
  "message": "Success",
  "source": "BRAND",
  "data": [{"id": "BRA00001", "name": "Apple", "tenant_id": 1}],
  "pagination": {"count": 1, "next": null, "previous": null}
}
```

Detail/create/update responses put one object in `data`. Lists put the records in `data` and navigation in `pagination`. Errors retain the envelope, set `data` to null, and add `errors` with field details. Successful DELETE returns HTTP 204 with an empty body.

Common statuses: 400 invalid input/dependency, 401 missing/invalid/revoked credentials, 403 insufficient permission or wrong admin password, 404 missing or another shop's resource, 429 login throttle exceeded.

## Verification

```powershell
python manage.py check
python manage.py test --settings=ps_backend.test_settings
python manage.py test --settings=ps_backend.postgres_test_settings --noinput
python manage.py makemigrations --check --dry-run --settings=ps_backend.test_settings
```

SQLite tests use an in-memory database. PostgreSQL tests use the configured connection credentials to create and remove a uniquely named test database; the database user needs CREATE DATABASE permission. Both test settings use a fast password hasher exclusively for tests and must never be used to run a deployed application.

Existing service modules remain internal ORM helpers. API views enforce authorization and serializer validation; call those APIs when integrating a frontend.
